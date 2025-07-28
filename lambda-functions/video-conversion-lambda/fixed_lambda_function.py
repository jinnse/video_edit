import json
import boto3
import urllib.parse
import os

# AWS 클라이언트 초기화
s3_client = boto3.client('s3')
mediaconvert_client = boto3.client('mediaconvert')

# 설정값
MEDIACONVERT_ROLE_ARN = 'arn:aws:iam::567279714866:role/MediaConvertServiceRole'
OUTPUT_BUCKET = 'video-output-pipeline-20250724'
MEDIACONVERT_ENDPOINT = None

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
    try:
        detail = event['detail']
        bucket_name = detail['bucket']['name']
        object_key = urllib.parse.unquote_plus(detail['object']['key'])
        
        print(f"🎬 처리할 파일: s3://{bucket_name}/{object_key}")
        
        input_format = get_video_format(object_key)
        if not input_format:
            print(f"❌ 지원하지 않는 파일 형식: {object_key}")
            return {
                'statusCode': 200,
                'body': json.dumps('지원하지 않는 동영상 파일이므로 처리하지 않음')
            }
        
        print(f"📹 입력 포맷: {input_format} → 출력 포맷: MP4")
        
        setup_mediaconvert_endpoint()
        
        job_id = create_mp4_conversion_job(bucket_name, object_key, input_format)
        
        if job_id:
            print(f"✅ MediaConvert 작업 생성 성공: {job_id}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'{input_format}을 MP4로 변환 작업이 시작되었습니다',
                    'job_id': job_id,
                    'input_file': f"s3://{bucket_name}/{object_key}",
                    'output_bucket': OUTPUT_BUCKET
                })
            }
        else:
            raise Exception("MediaConvert 작업 생성 실패")
            
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def get_video_format(file_key):
    file_extension = os.path.splitext(file_key.lower())[1]
    return SUPPORTED_VIDEO_FORMATS.get(file_extension)

def setup_mediaconvert_endpoint():
    global mediaconvert_client, MEDIACONVERT_ENDPOINT
    if not MEDIACONVERT_ENDPOINT:
        try:
            response = mediaconvert_client.describe_endpoints()
            MEDIACONVERT_ENDPOINT = response['Endpoints'][0]['Url']
            mediaconvert_client = boto3.client('mediaconvert', endpoint_url=MEDIACONVERT_ENDPOINT)
            print(f"🔗 MediaConvert 엔드포인트 설정: {MEDIACONVERT_ENDPOINT}")
        except Exception as e:
            print(f"❌ MediaConvert 엔드포인트 설정 실패: {e}")
            raise

def create_mp4_conversion_job(input_bucket, input_key, input_format):
    file_name = input_key.split('/')[-1]
    name_without_ext = os.path.splitext(file_name)[0]

    input_path = f"s3://{input_bucket}/{input_key}"
    output_path = f"s3://{OUTPUT_BUCKET}/converted/"
    
    print(f"📁 입력: {input_path}")
    print(f"📁 출력: {output_path}{file_name}")
    
    job_settings = {
        "Role": MEDIACONVERT_ROLE_ARN,
        "Settings": {
            "Inputs": [
                {
                    "FileInput": input_path,
                    "AudioSelectors": {
                        "Audio Selector 1": {
                            "DefaultSelection": "DEFAULT"
                        }
                    },
                    "VideoSelector": {}
                }
            ],
            "OutputGroups": [
                {
                    "Name": "MP4_Output",
                    "OutputGroupSettings": {
                        "Type": "FILE_GROUP_SETTINGS",
                        "FileGroupSettings": {
                            "Destination": output_path
                        }
                    },
                    "Outputs": [
                        {
                            # NameModifier 제거됨 ✅
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
                            "AudioDescriptions": [
                                {
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
                                }
                            ],
                            "ContainerSettings": {
                                "Container": "MP4"
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        response = mediaconvert_client.create_job(**job_settings)
        job_id = response['Job']['Id']
        print(f"🎬 MediaConvert 작업 생성됨: {job_id}")
        return job_id
    except Exception as e:
        print(f"❌ MediaConvert 작업 생성 실패: {e}")
        return None
