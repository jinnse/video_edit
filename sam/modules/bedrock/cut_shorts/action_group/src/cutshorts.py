import json
import boto3
import os
import time
import re
from datetime import datetime
from typing import Optional

# ===================== 하드코딩된 설정값 =====================
VIDEO_BUCKET = "video-input-pipeline-20250724"
SOURCE_BUCKET_DEFAULT = VIDEO_BUCKET
DEFAULT_PREFIX = "original/"
OUTPUT_PREFIX = "output/"
THUMBNAIL_PREFIX = "thumbnails/"
THUMBNAIL_ENABLED = True
THUMBNAIL_TIME = 1
MEDIACONVERT_ROLE_ARN = "arn:aws:iam::567279714866:role/MediaConvertServiceRole"

# 인덱스 패턴 (media_th.py에서 가져옴)
INDEXED_JPG_PATTERN = re.compile(r'^([^/]+?)\.(\d+)\.jpg$', re.IGNORECASE)

# ===================== 유틸리티 함수 =====================
def ensure_prefix(p: str) -> str:
    return p if p.endswith("/") else (p + "/")

def parse_time_to_seconds(time_str):
    if not time_str:
        return 0.0

    try:
        s = str(time_str).strip()
        parts = s.split(":")

        if len(parts) == 3:  # HH:MM:SS
            h, m, sec = int(parts[0]), int(parts[1]), float(parts[2])
            return h*3600 + m*60 + sec

        elif len(parts) == 2:  # MM:SS
            m, sec = int(parts[0]), float(parts[1])
            return m*60 + sec

        elif len(parts) == 1:  # SS
            return float(parts[0])

    except ValueError:
        # 잘못된 값이 들어온 경우
        return None

def seconds_to_time_format(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def seconds_to_timecode(seconds, fps=29.97):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    frames = 0
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"

def error_json(msg, action_group="default", function_name="default", details=None):
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function_name,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": json.dumps({
                            "success": False,
                            "error": msg,
                            "details": details
                        }, ensure_ascii=False)
                    }
                }
            }
        }
    }

# ===================== 파일명 관련 함수 =====================
def sanitize_basename(name: str) -> str:
    import re
    name = name.replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "", name) or "video"

def build_output_names(base_name: str, scenes, ts_str: str):
    base = sanitize_basename(base_name)
    
    # 첫 번째 장면의 시작 시간과 마지막 장면의 끝 시간을 사용
    first_start = parse_time_to_seconds(scenes[0].get("start_time"))
    last_end = parse_time_to_seconds(scenes[-1].get("end_time"))
    
    out_name = f"{base}_{int(first_start)}s-{int(last_end)}s_short.mp4"
    thumb_name = f"{base}_{int(first_start)}s-{int(last_end)}s_short.jpg"
    
    return out_name, thumb_name

# ===================== S3 관련 함수 =====================
def extract_source_from_prompt(prompt_text: str):
    text = prompt_text or ""

    # 1) s3 URI
    m = re.search(r's3://([^/\s]+)/(?:\s*)?([^\s"\'<>]+)', text)
    if m:
        bucket = m.group(1).strip()
        key = m.group(2).strip()
        print(f"✅ s3 URI 감지: bucket={bucket}, key={key}")
        return bucket, key

    # 2) parameters에서 video_input 찾기
    if "parameters" in text or "video_input" in text:
        video_match = re.search(r'"video_input"\s*:\s*"([^"]+)"', text)
        if video_match:
            video_file = video_match.group(1).strip()
            if not "/" in video_file and not video_file.startswith(DEFAULT_PREFIX):
                video_file = f"{DEFAULT_PREFIX}{video_file}"
            print(f"✅ parameters에서 video_input 감지: key={video_file}")
            return SOURCE_BUCKET_DEFAULT, video_file

    # 3) 일반적인 비디오 파일 확장자로 끝나는 파일명 찾기
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    for ext in video_extensions:
        pattern = rf'([^/\s"\'<>]+{re.escape(ext)})'
        matches = re.findall(pattern, text)
        if matches:
            video_file = matches[0].strip()
            if not "/" in video_file and not video_file.startswith(DEFAULT_PREFIX):
                video_file = f"{DEFAULT_PREFIX}{video_file}"
            print(f"✅ 비디오 파일 확장자 감지: key={video_file}")
            return SOURCE_BUCKET_DEFAULT, video_file

    # 4) 토큰들에서 경로/파일처럼 보이는 후보 찾기
    tokens = re.findall(r'([^\s"\'<>]+)', text)
    for t in reversed(tokens):
        if "." in t and len(t) > 3 and len(t) < 100:
            if not re.search(r'[가-힣]{3,}', t) and not re.search(r'[^\w\-_.]', t):
                cleaned = t.strip()
                print(f"✅ 경로/파일 토큰 감지: key={cleaned}")
                return SOURCE_BUCKET_DEFAULT, cleaned

    # 5) fallback - 기본값 사용
    print(f"⚠️ 키 감지 실패 → 기본값 사용")
    return SOURCE_BUCKET_DEFAULT, f"{DEFAULT_PREFIX}video.mp4"

def s3_key_exists(bucket: str, key: str) -> bool:
    s3 = boto3.client("s3")
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        print(f"ℹ️ head_object 실패: s3://{bucket}/{key} ({e})")
        return False

# ===================== MediaConvert Assembly Workflow 함수 =====================
def create_shorts_with_assembly_workflow(input_s3_uri, output_s3_uri, scenes, output_filename, generate_thumbnail=True):
    """
    MediaConvert Assembly Workflow를 사용하여 한 번의 Job으로 숏츠 생성
    """
    print(f"🎬 MediaConvert Assembly Workflow 숏츠 생성 시작: {len(scenes)}개 장면")
    
    mediaconvert = boto3.client('mediaconvert', region_name='ap-northeast-2')
    
    # 출력 파일명에서 확장자 제거
    base_filename = output_filename.replace('.mp4', '')
    
    # 썸네일 출력 경로 설정
    thumbnail_output_dir = f"s3://{VIDEO_BUCKET}/{THUMBNAIL_PREFIX}"
    
    # InputClipping 설정 생성
    input_clippings = []
    for i, scene in enumerate(scenes):
        start_time = parse_time_to_seconds(scene.get("start_time"))
        end_time = parse_time_to_seconds(scene.get("end_time"))
        
        input_clippings.append({
            "StartTimecode": seconds_to_timecode(start_time),
            "EndTimecode": seconds_to_timecode(end_time)
        })
        print(f"📋 장면 {i+1}: {start_time}s ~ {end_time}s")
    
    job_settings = {
        "TimecodeConfig": {
            "Source": "ZEROBASED"
        },
        "Inputs": [
            {
                "FileInput": input_s3_uri,
                "TimecodeSource": "ZEROBASED",
                "InputClippings": input_clippings,
                "AudioSelectors": {
                    "Audio Selector 1": {
                        "DefaultSelection": "DEFAULT"
                    }
                }
            }
        ],
        "OutputGroups": [
            {
                "Name": "File Group",
                "OutputGroupSettings": {
                    "Type": "FILE_GROUP_SETTINGS",
                    "FileGroupSettings": {
                        "Destination": output_s3_uri.replace(f"/{output_filename}", "/")
                    }
                },
                "Outputs": [
                    {
                        "NameModifier": "_short",
                        "VideoDescription": {
                            "CodecSettings": {
                                "Codec": "H_264",
                                "H264Settings": {
                                    "RateControlMode": "QVBR",
                                    "QvbrSettings": {
                                        "QvbrQualityLevel": 8
                                    },
                                    "MaxBitrate": 5000000,
                                    "AdaptiveQuantization": "HIGH",
                                    "EntropyEncoding": "CABAC",
                                    "FramerateControl": "INITIALIZE_FROM_SOURCE",
                                    "FramerateConversionAlgorithm": "DUPLICATE_DROP",
                                    "CodecProfile": "MAIN",
                                    "SlowPal": "DISABLED",
                                    "SpatialAdaptiveQuantization": "ENABLED",
                                    "Syntax": "DEFAULT",
                                    "TemporalAdaptiveQuantization": "ENABLED"
                                }
                            }
                        },
                        "AudioDescriptions": [
                            {
                                "AudioSourceName": "Audio Selector 1",
                                "CodecSettings": {
                                    "Codec": "AAC",
                                    "AacSettings": {
                                        "CodecProfile": "LC",
                                        "RateControlMode": "CBR",
                                        "Bitrate": 128000,
                                        "SampleRate": 48000,
                                        "RawFormat": "NONE",
                                        "Specification": "MPEG4",
                                        "CodingMode": "CODING_MODE_2_0"
                                    }
                                }
                            }
                        ],
                        "ContainerSettings": {
                            "Container": "MP4",
                            "Mp4Settings": {
                                "CslgAtom": "INCLUDE",
                                "FreeSpaceBox": "EXCLUDE",
                                "MoovPlacement": "PROGRESSIVE_DOWNLOAD"
                            }
                        }
                    }
                ]
            }
        ]
    }
    
    # 썸네일 생성이 활성화된 경우 썸네일 출력 그룹 추가
    if generate_thumbnail and THUMBNAIL_ENABLED:
        job_settings["OutputGroups"].append({
            "Name": "Thumbnail",
            "OutputGroupSettings": {
                "Type": "FILE_GROUP_SETTINGS",
                "FileGroupSettings": {
                    "Destination": thumbnail_output_dir
                }
            },
            "Outputs": [
                {
                    "NameModifier": "_short",
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
                }
            ]
        })
        print(f"🖼️ 썸네일 생성 활성화: {thumbnail_output_dir}")

    try:
        response = mediaconvert.create_job(
            Role=MEDIACONVERT_ROLE_ARN,
            Settings=job_settings,
            StatusUpdateInterval='SECONDS_10',
            UserMetadata={
                'type': 'assembly_workflow',
                'scene_count': str(len(scenes)),
                'output_filename': output_filename
            }
        )
        
        job_id = response['Job']['Id']
        print(f"✅ MediaConvert Assembly Workflow Job 생성 성공: {job_id}")
        return True, job_id
        
    except Exception as e:
        print(f"❌ MediaConvert Assembly Workflow Job 생성 실패: {e}")
        return False, None

def wait_for_mediaconvert_job(job_id, timeout_seconds=300):
    print(f"⏳ MediaConvert Job 완료 대기: {job_id}")
    mediaconvert = boto3.client('mediaconvert', region_name='ap-northeast-2')
    
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            response = mediaconvert.get_job(Id=job_id)
            status = response['Job']['Status']
            
            if status == 'COMPLETE':
                print(f"✅ MediaConvert Job 완료: {job_id}")
                return True
            elif status == 'ERROR':
                error_message = response['Job'].get('ErrorMessage', 'Unknown error')
                print(f"❌ MediaConvert Job 실패: {error_message}")
                return False
            elif status in ['SUBMITTED', 'PROGRESSING']:
                print(f"⏳ MediaConvert Job 진행 중: {status}")
                time.sleep(10)
            else:
                print(f"⚠️ MediaConvert Job 상태: {status}")
                time.sleep(10)
                
        except Exception as e:
            print(f"❌ MediaConvert Job 상태 확인 실패: {e}")
            return False
    
    print(f"⏰ MediaConvert Job 타임아웃: {job_id}")
    return False

# ===================== 썸네일 관련 함수 =====================
def find_indexed_thumbnail(bucket: str, prefix: str, base: str):
    """
    thumbnails/ 아래에서 <base>.<숫자>.jpg 를 찾아 키를 반환.
    없으면 None.
    """
    target_prefix = f"{prefix}{base}"
    s3 = boto3.client("s3")
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=target_prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']  # thumbnails/base.0000000.jpg
                filename = key[len(prefix):]  # base.0000000.jpg
                if INDEXED_JPG_PATTERN.match(filename):
                    print(f"🔎 인덱스 썸네일 발견: s3://{bucket}/{key}")
                    return key
    except Exception as e:
        print(f"⚠️ 썸네일 검색 중 오류: {e}")
    
    # 더 넓은 범위로 검색 (base 이름의 일부만으로도 검색)
    try:
        print(f"🔍 더 넓은 범위로 썸네일 검색 중...")
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']  # thumbnails/...
                filename = key[len(prefix):]  # base.0000000.jpg
                if INDEXED_JPG_PATTERN.match(filename):
                    # base 이름이 파일명에 포함되어 있는지 확인
                    if base in filename:
                        print(f"🔎 인덱스 썸네일 발견 (확장 검색): s3://{bucket}/{key}")
                        return key
    except Exception as e:
        print(f"⚠️ 확장 썸네일 검색 중 오류: {e}")
    
    print(f"⚠️ 인덱스 썸네일을 못 찾음: s3://{bucket}/{prefix}{base}.<num>.jpg")
    return None

def rename_indexed_thumbnail(bucket: str, base_name: str, indexed_key: str):
    """
    s3://<bucket>/thumbnails/<base>.<번호>.jpg → s3://<bucket>/thumbnails/<base>.jpg 로 리네임(copy→delete)
    """
    final_key = f"{THUMBNAIL_PREFIX}{base_name}.jpg"
    print(f"🖼️ 썸네일 리네임: s3://{bucket}/{indexed_key} → s3://{bucket}/{final_key}")
    
    try:
        s3 = boto3.client("s3")
        s3.copy(
            CopySource={"Bucket": bucket, "Key": indexed_key},
            Bucket=bucket,
            Key=final_key
        )
        s3.delete_object(Bucket=bucket, Key=indexed_key)
        print("✅ 썸네일 리네임 완료 (copy→delete)")
        return final_key
    except Exception as e:
        print(f"❌ 썸네일 리네임 실패: {e}")
        return None

def process_thumbnail_after_job(bucket: str, base_name: str):
    """
    MediaConvert Job 완료 후 썸네일 처리
    """
    if not THUMBNAIL_ENABLED:
        print("⚠️ 썸네일 생성이 비활성화됨")
        return None
        
    print(f"🖼️ 썸네일 처리 시작... (base_name: {base_name})")
    
    # 인덱스 썸네일 찾기 (NameModifier가 포함된 파일명으로 검색)
    indexed_key = find_indexed_thumbnail(bucket, THUMBNAIL_PREFIX, base_name)
    if not indexed_key:
        # 혹시 이미 리네임되어 있을 수도 있으니 최종 파일 존재도 체크
        final_key = f"{THUMBNAIL_PREFIX}{base_name}.jpg"
        try:
            s3 = boto3.client("s3")
            s3.head_object(Bucket=bucket, Key=final_key)
            print(f"ℹ️ 최종 썸네일 이미 존재: s3://{bucket}/{final_key}")
            return final_key
        except:
            print(f"❌ 썸네일을 찾을 수 없음: {base_name}")
            return None
    
    # 썸네일 리네임
    final_key = rename_indexed_thumbnail(bucket, base_name, indexed_key)
    if final_key:
        print(f"✅ 썸네일 처리 완료: s3://{bucket}/{final_key}")
        return final_key
    
    return None

# ===================== 메인 핸들러 =====================
def lambda_handler(event, context):
    try:
        print("🚀 MediaConvert Assembly Workflow 숏츠 생성 Lambda 시작")
        print(json.dumps(event, indent=2, ensure_ascii=False))
        
        start_time = time.time()
        
        action_group = event.get("actionGroup", "default")
        function_name = event.get("function", "default")
        input_text = event.get("inputText", "")
        
        # 액션 파라미터 추출
        params = {}
        if "parameters" in event:
            for p in event["parameters"]:
                params[p.get("name", "")] = p.get("value", "")
        
        # 입력 데이터 처리
        scenes_to_process = []
        
        # 1) parameters에서 개별 장면 처리
        if params and "start_time" in params and "end_time" in params:
            start_time = parse_time_to_seconds(params.get("start_time"))
            end_time = parse_time_to_seconds(params.get("end_time"))
            
            if start_time >= 0 and end_time > start_time:
                scenes_to_process.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "video_input": params.get("video_input", "soccer.mp4")
                })
                print(f"✅ parameters에서 장면 감지: {start_time}s ~ {end_time}s")
        
        # 2) JSON에서 scenes 배열 처리 개선
        if not scenes_to_process:
            try:
                # 방법 1: 전체 텍스트를 JSON으로 직접 파싱 시도
                input_data = json.loads(input_text)
                scenes_to_process = input_data.get("scenes", [])
                print(f"✅ 직접 JSON 파싱으로 {len(scenes_to_process)}개 장면 감지")
            except json.JSONDecodeError:
                try:
                    # 방법 2: { 로 시작하는 JSON 객체 찾기 (개선된 패턴)
                    json_start = input_text.find('{')
                    json_end = input_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_content = input_text[json_start:json_end]
                        input_data = json.loads(json_content)
                        scenes_to_process = input_data.get("scenes", [])
                        print(f"✅ 부분 JSON 추출로 {len(scenes_to_process)}개 장면 감지")
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON 파싱 완전 실패: {e}")
                    print(f"⚠️ 입력 텍스트: {input_text[:500]}...")
        
        # 3) 장면이 없으면 오류
        if not scenes_to_process:
            return error_json("처리할 장면이 없습니다. start_time/end_time 파라미터 또는 scenes 배열이 필요합니다.", action_group, function_name)
        
        print(f"📋 처리할 장면 수: {len(scenes_to_process)}")
        
        # --- 프롬프트에서 (source_bucket, source_key) 추출 ---
        source_bucket, source_key = extract_source_from_prompt(input_text)
        
        # 키 감지 실패 시 기본값 사용
        if source_bucket is None or source_key is None:
            print(f"⚠️ 키 감지 실패 → 기본값 사용")
            source_bucket = SOURCE_BUCKET_DEFAULT
            source_key = f"{DEFAULT_PREFIX}video.mp4"
        
        # S3 경로/버킷 설정
        output_bucket = VIDEO_BUCKET
        base_name, _ = os.path.splitext(os.path.basename(source_key))
        base_name = base_name or "video"
        
        # 출력 파일명 생성
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename, thumbnail_filename = build_output_names(base_name, scenes_to_process, ts)
        
        # MediaConvert용 파일명 생성 (NameModifier를 고려)
        first_start = parse_time_to_seconds(scenes_to_process[0].get("start_time"))
        last_end = parse_time_to_seconds(scenes_to_process[-1].get("end_time"))
        mediaconvert_base_name = f"{base_name}_{int(first_start)}s-{int(last_end)}s"
        
        # MediaConvert에서 시간 정보가 포함된 파일명을 생성하려면
        # 원본 파일명을 변경해야 함
        output_key = f"{OUTPUT_PREFIX}{mediaconvert_base_name}_short.mp4"
        output_s3_uri = f"s3://{output_bucket}/{output_key}"
        
        # 입력 S3 URI
        input_s3_uri = f"s3://{source_bucket}/{source_key}"
        
        print(f"🎬 MediaConvert Assembly Workflow 시작")
        print(f"📥 입력: {input_s3_uri}")
        print(f"📤 출력: {output_s3_uri}")
        
        # MediaConvert Assembly Workflow 실행
        success, job_id = create_shorts_with_assembly_workflow(
            input_s3_uri,
            output_s3_uri,
            scenes_to_process,
            output_filename,
            generate_thumbnail=True
        )
        
        if not success:
            return error_json("MediaConvert Assembly Workflow Job 생성 실패", action_group, function_name)
        
        # Job 완료 대기
        if not wait_for_mediaconvert_job(job_id):
            return error_json("MediaConvert Assembly Workflow Job 실패", action_group, function_name)
        
        # 실제 생성된 파일명 찾기 및 리네임
        s3 = boto3.client("s3")
        actual_filename = None
        file_size_mb = 0
        
        try:
            # S3에서 _short.mp4로 끝나는 파일 찾기
            response = s3.list_objects_v2(
                Bucket=output_bucket,
                Prefix=OUTPUT_PREFIX,
                MaxKeys=100
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('_short.mp4'):
                        # MediaConvert가 생성한 파일을 원하는 이름으로 리네임
                        old_key = key
                        new_key = f"{OUTPUT_PREFIX}{mediaconvert_base_name}_short.mp4"
                        
                        if old_key != new_key:
                            print(f"🔄 파일 리네임: {os.path.basename(old_key)} → {os.path.basename(new_key)}")
                            s3.copy(
                                CopySource={"Bucket": output_bucket, "Key": old_key},
                                Bucket=output_bucket,
                                Key=new_key
                            )
                            s3.delete_object(Bucket=output_bucket, Key=old_key)
                            print(f"✅ 파일 리네임 완료")
                        
                        actual_filename = os.path.basename(new_key)
                        file_size = obj['Size']
                        file_size_mb = file_size / (1024 * 1024)
                        print(f"✅ 최종 파일명: {actual_filename}")
                        print(f"📄 출력 파일 크기: {file_size:,} bytes ({file_size_mb:.1f}MB)")
                        break
            
            if not actual_filename:
                # 기존 방식으로 시도
                response = s3.head_object(Bucket=output_bucket, Key=output_key)
                file_size = response['ContentLength']
                file_size_mb = file_size / (1024 * 1024)
                actual_filename = os.path.basename(output_key)
                print(f"📄 출력 파일명: {actual_filename}")
                print(f"📄 출력 파일 크기: {file_size:,} bytes ({file_size_mb:.1f}MB)")
                
        except Exception as e:
            print(f"⚠️ 파일 크기 확인 실패: {e}")
            actual_filename = os.path.basename(output_key)
        
        # 썸네일 처리 및 리네임
        thumbnail_key = None
        if THUMBNAIL_ENABLED:
            # MediaConvert가 생성한 썸네일을 원하는 이름으로 리네임
            old_thumb_key = f"{THUMBNAIL_PREFIX}{base_name}_short.jpg"
            new_thumb_key = f"{THUMBNAIL_PREFIX}{mediaconvert_base_name}_short.jpg"
            
            try:
                # 기존 썸네일 처리 (인덱스 파일 찾기 및 리네임)
                base_name_for_thumb = f"{base_name}_short"
                thumbnail_key = process_thumbnail_after_job(output_bucket, base_name_for_thumb)
                
                # 추가로 시간 정보가 포함된 이름으로 리네임
                if thumbnail_key and thumbnail_key != new_thumb_key:
                    print(f"🔄 썸네일 리네임: {os.path.basename(thumbnail_key)} → {os.path.basename(new_thumb_key)}")
                    s3.copy(
                        CopySource={"Bucket": output_bucket, "Key": thumbnail_key},
                        Bucket=output_bucket,
                        Key=new_thumb_key
                    )
                    s3.delete_object(Bucket=output_bucket, Key=thumbnail_key)
                    thumbnail_key = new_thumb_key
                    print(f"✅ 썸네일 리네임 완료")
                    
            except Exception as e:
                print(f"⚠️ 썸네일 리네임 실패: {e}")
                # 기존 썸네일 처리 결과 사용
                base_name_for_thumb = f"{base_name}_short"
                thumbnail_key = process_thumbnail_after_job(output_bucket, base_name_for_thumb)
        
        # 장면 정보 요약
        scene_summary = []
        total_duration = 0
        for i, scene in enumerate(scenes_to_process):
            start_time = parse_time_to_seconds(scene.get("start_time"))
            end_time = parse_time_to_seconds(scene.get("end_time"))
            duration = end_time - start_time
            total_duration += duration
            
            scene_summary.append(f"{i+1}. {seconds_to_time_format(start_time)} ~ {seconds_to_time_format(end_time)} ({seconds_to_time_format(duration)})")
        
        # 응답 메시지 생성
        response_message = f"""숏츠 영상 생성 완료! MediaConvert Assembly Workflow를 사용하여 {len(scenes_to_process)}개 장면을 한 번에 처리했습니다.

생성된 파일명: {actual_filename}
파일 크기: {file_size_mb:.1f}MB
총 재생 시간: {seconds_to_time_format(total_duration)}

처리된 장면:
{chr(10).join(scene_summary)}

저장 위치: S3 버킷 '{output_bucket}'의 '{OUTPUT_PREFIX}' 폴더
처리 방식: MediaConvert Assembly Workflow (InputClipping)"""

        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "function": function_name,
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": response_message
                        }
                    }
                }
            }
        }

    except Exception as e:
        import traceback
        print("❌ Lambda 오류:", e)
        print(traceback.format_exc())
        return error_json("Lambda 함수 실행 오류", event.get("actionGroup","default"),
                          event.get("function","default"), str(e))