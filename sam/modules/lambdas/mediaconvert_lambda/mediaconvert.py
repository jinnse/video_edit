import json
import boto3
import urllib.parse
import os
import re

# ---------- AWS Clients ----------
s3_client = boto3.client('s3')
mediaconvert_client = boto3.client('mediaconvert')

# ---------- Config ----------
MEDIACONVERT_ROLE_ARN = 'arn:aws:iam::567279714866:role/MediaConvertServiceRole'
OUTPUT_BUCKET = 'video-output-pipeline-20250724'  # 다운그레이드 MP4는 기존 경로 그대로
THUMBNAIL_PREFIX = 'original/thumbnails/'         # 최종: s3://<입력버킷>/original/thumbnails/<영상이름>.jpg
MEDIACONVERT_ENDPOINT = None

# 썸네일 S3 ObjectCreated 시, 인덱스 파일 패턴 (예: soccer.000000.jpg 또는 0000000 등)
INDEXED_JPG_PATTERN = re.compile(r'^original/thumbnails/([^/]+)\.(\d+)\.jpg$', re.IGNORECASE)

# 지원하는 입력 동영상 포맷
SUPPORTED_VIDEO_FORMATS = {
    '.mp4': 'MP4',
    '.mov': 'QuickTime',
    '.avi': 'AVI',
    '.mkv': 'Matroska',
    '.wmv': 'Windows Media',
    '.flv': 'Flash Video',
    '.webm': 'WebM',
    '.m4v': 'iTunes Video'
}

def lambda_handler(event, context):
    """
    하나의 Lambda가 두 케이스를 처리:
      1) S3 Object Created (원본 동영상)  -> MediaConvert 잡 생성 (MP4 + 썸네일)
      2) S3 Object Created (썸네일 인덱스 파일) -> 즉시 리네임( copy -> delete )
    EventBridge(detail) & S3 Notifications(Records) 둘 다 지원.
    """
    try:
        # 1) 이벤트에서 버킷/키 파싱
        #bucket, key = extract_bucket_key(event)

        bucket = event["detail"]["bucket"]["name"]
        key = event["detail"]["object"]["key"]
        if not bucket or not key:
            print(f"❌ 이벤트 파싱 실패: {json.dumps(event)[:500]}")
            return resp(400, "Unsupported event format")

        key = urllib.parse.unquote_plus(key)
        print(f"📦 Event object: s3://{bucket}/{key}")

        # 2) 썸네일 인덱스 파일이면 → 즉시 리네임
        m = INDEXED_JPG_PATTERN.match(key)
        if m:
            base = m.group(1)  # 영상이름
            return rename_indexed_thumbnail(bucket, base, key)

        # 3) 최종 썸네일(인덱스 없는 .jpg)이면 → 재트리거 방지로 스킵
        if key.startswith(THUMBNAIL_PREFIX) and key.lower().endswith('.jpg'):
            print(f"⏭️ Final thumbnail detected; skip: s3://{bucket}/{key}")
            return resp(200, "Skipped final thumbnail")

        # 4) 원본 동영상이면 → MediaConvert 잡 생성
        if not is_supported_video(key):
            print(f"⏭️ 지원하지 않는 확장자 또는 비동영상: {key}")
            return resp(200, "Unsupported or non-video; skipped")

        print(f"🎬 처리할 파일(원본): s3://{bucket}/{key}")
        print("📹 출력: MP4(기존 경로 유지) + Thumbnail(폴더만 지정)")

        setup_mediaconvert_endpoint()
        job_id = create_mediaconvert_job(bucket, key)

        if not job_id:
            raise Exception("MediaConvert 작업 생성 실패")

        print(f"✅ MediaConvert 작업 생성 성공: {job_id}")
        return resp(200, {
            "message": "Transcode + thumbnail job started",
            "job_id": job_id,
            "input": f"s3://{bucket}/{key}"
        })

    except Exception as e:
        print(f"❌ 오류: {e}")
        return resp(500, {"error": str(e)})

# ---------- Core helpers ----------

# def extract_bucket_key(event: dict):
#     """
#     EventBridge(S3 Object Created: event['detail']) 또는 S3 Notification(Records)을 모두 지원.
#     """
#     # EventBridge
#     detail = event.get('detail')
#     if detail and 'bucket' in detail and 'object' in detail:
#         return detail['bucket']['name'], detail['object']['key']

#     # S3 Notification
#     records = event.get('Records')
#     if records:
#         rec = records[0]
#         return rec['s3']['bucket']['name'], rec['s3']['object']['key']

#     return None, None


def is_supported_video(key: str) -> bool:
    ext = os.path.splitext(key.lower())[1]
    return ext in SUPPORTED_VIDEO_FORMATS

def setup_mediaconvert_endpoint():
    global mediaconvert_client, MEDIACONVERT_ENDPOINT
    if MEDIACONVERT_ENDPOINT:
        return
    response = mediaconvert_client.describe_endpoints()
    MEDIACONVERT_ENDPOINT = response['Endpoints'][0]['Url']
    mediaconvert_client = boto3.client('mediaconvert', endpoint_url=MEDIACONVERT_ENDPOINT)
    print(f"🔗 MediaConvert 엔드포인트 설정: {MEDIACONVERT_ENDPOINT}")

def create_mediaconvert_job(input_bucket: str, input_key: str) -> str:
    """
    - MP4: s3://video-output-pipeline-20250724/converted/  (기존 유지)
    - 썸네일: s3://<input_bucket>/original/thumbnails/   (폴더만 지정 → {base}.000000.jpg 생성)
    - 1초 지점 1장 캡처 (원하면 InputClippings 제거 가능)
    """
    file_name = os.path.basename(input_key)
    base = os.path.splitext(file_name)[0]

    input_path = f"s3://{input_bucket}/{input_key}"
    mp4_output_dir = f"s3://{OUTPUT_BUCKET}/converted/"           # 폴더 (슬래시 필수)
    thumb_output_dir = f"s3://{input_bucket}/{THUMBNAIL_PREFIX}"  # 폴더 (파일명 X)

    print(f"📁 입력: {input_path}")
    print(f"📁 MP4 출력 폴더: {mp4_output_dir}")
    print(f"🖼️ 썸네일 출력 폴더: {thumb_output_dir}")

    job_settings = {
        "Role": MEDIACONVERT_ROLE_ARN,
        "UserMetadata": {
            # 리네임엔 필요없지만, 추후 디버깅 용도로 남겨둠
            "thumb_bucket": input_bucket,
            "thumb_prefix": THUMBNAIL_PREFIX,
            "base_name": base
        },
        "Settings": {
            "Inputs": [{
                "FileInput": input_path,
                "TimecodeSource": "ZEROBASED",
                "InputClippings": [
                    {"StartTimecode": "00:00:01:00", "EndTimecode": "00:00:01:01"}
                ],
                "AudioSelectors": {
                    "Audio Selector 1": {"DefaultSelection": "DEFAULT"}
                },
                "VideoSelector": {}
            }],
            "OutputGroups": [
                # MP4 변환 (그대로)
                {
                    "Name": "MP4_Output",
                    "OutputGroupSettings": {
                        "Type": "FILE_GROUP_SETTINGS",
                        "FileGroupSettings": {"Destination": mp4_output_dir}
                    },
                    "Outputs": [{
                        "VideoDescription": {
                            "Width": 720,
                            "Height": 480,
                            "CodecSettings": {
                                "Codec": "H_264",
                                "H264Settings": {
                                    "Bitrate": 2000000,
                                    "FramerateControl": "INITIALIZE_FROM_SOURCE",
                                    "RateControlMode": "CBR"
                                }
                            }
                        },
                        "AudioDescriptions": [{
                            "AudioSourceName": "Audio Selector 1",
                            "CodecSettings": {
                                "Codec": "AAC",
                                "AacSettings": {
                                    "Bitrate": 128000,
                                    "RateControlMode": "CBR",
                                    "SampleRate": 48000,
                                    "CodingMode": "CODING_MODE_2_0"
                                }
                            }
                        }],
                        "ContainerSettings": {"Container": "MP4"}
                    }]
                },
                # 썸네일 (프레임 캡처)
                {
                    "Name": "Thumbnail",
                    "OutputGroupSettings": {
                        "Type": "FILE_GROUP_SETTINGS",
                        "FileGroupSettings": {"Destination": thumb_output_dir}
                    },
                    "Outputs": [{
                        # ⚠️ NameModifier 넣지 않음 → 기본 규칙: <base>.000000.jpg
                        "Extension": "jpg",
                        "ContainerSettings": {"Container": "RAW"},
                        "VideoDescription": {
                            "CodecSettings": {
                                "Codec": "FRAME_CAPTURE",
                                "FrameCaptureSettings": {
                                    "FramerateNumerator": 1,
                                    "FramerateDenominator": 1,
                                    "MaxCaptures": 1,
                                    "Quality": 80
                                }
                            }
                        }
                    }]
                }
            ]
        }
    }

    try:
        resp = mediaconvert_client.create_job(**job_settings)
        job_id = resp['Job']['Id']
        print(f"🎬 MediaConvert 작업 생성됨: {job_id}")
        return job_id
    except Exception as e:
        print(f"❌ MediaConvert 작업 생성 실패: {e}")
        return None

def rename_indexed_thumbnail(bucket: str, base_name: str, indexed_key: str):
    """
    s3://<bucket>/original/thumbnails/<base>.000000.jpg → same prefix/<base>.jpg 로 리네임(copy→delete)
    S3 이벤트만으로 처리 (별도 MediaConvert COMPLETE 규칙 불필요)
    """
    final_key = f"{THUMBNAIL_PREFIX}{base_name}.jpg"

    # 최종 파일이 이미 존재하면 덮어쓰기(원하면 조건부로 변경 가능)
    print(f"🖼️ Rename thumbnail: s3://{bucket}/{indexed_key} → s3://{bucket}/{final_key}")
    try:
        s3_client.copy(
            CopySource={"Bucket": bucket, "Key": indexed_key},
            Bucket=bucket,
            Key=final_key
        )
        s3_client.delete_object(Bucket=bucket, Key=indexed_key)
        print("✅ Renamed (copy→delete) complete")
        return resp(200, {"thumbnail": f"s3://{bucket}/{final_key}"})
    except Exception as e:
        print(f"❌ Rename failed: {e}")
        return resp(500, {"error": f"rename failed: {str(e)}"})

# ---------- Utils ----------
def resp(code, body):
    if not isinstance(body, (str, dict, list)):
        body = str(body)
    return {"statusCode": code, "body": json.dumps(body)}
