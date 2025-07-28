import json
import boto3
import uuid
import os
from urllib.parse import unquote_plus

def lambda_handler(event, context):
    """
    S3에 업로드된 비디오 파일을 MediaConvert를 사용해 변환하는 Lambda 함수
    """
    
    # 환경 변수
    OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
    MEDIACONVERT_ROLE_ARN = os.environ['MEDIACONVERT_ROLE_ARN']
    
    # AWS 클라이언트 초기화
    mediaconvert = boto3.client('mediaconvert', region_name='ap-northeast-2')
    
    try:
        # EventBridge에서 온 이벤트 파싱
        bucket_name = event['detail']['bucket']['name']
        object_key = unquote_plus(event['detail']['object']['key'])
        
        print(f"Processing file: s3://{bucket_name}/{object_key}")
        
        # MediaConvert 엔드포인트 가져오기
        endpoints = mediaconvert.describe_endpoints()
        endpoint_url = endpoints['Endpoints'][0]['Url']
        mediaconvert_client = boto3.client('mediaconvert', endpoint_url=endpoint_url, region_name='ap-northeast-2')
        
        # 파일명에서 확장자 제거
        filename_without_ext = os.path.splitext(os.path.basename(object_key))[0]
        
        # MediaConvert 작업 설정
        job_settings = {
            "Role": MEDIACONVERT_ROLE_ARN,
            "Settings": {
                "OutputGroups": [
                    {
                        "Name": "File Group",
                        "OutputGroupSettings": {
                            "Type": "FILE_GROUP_SETTINGS",
                            "FileGroupSettings": {
                                "Destination": f"s3://{OUTPUT_BUCKET}/converted/"
                            }
                        },
                        "Outputs": [
                            {
                                "NameModifier": f"_{filename_without_ext}_converted",
                                "ContainerSettings": {
                                    "Container": "MP4"
                                },
                                "VideoDescription": {
                                    "CodecSettings": {
                                        "Codec": "H_264",
                                        "H264Settings": {
                                            "RateControlMode": "QVBR",
                                            "QvbrSettings": {
                                                "QvbrQualityLevel": 7
                                            }
                                        }
                                    }
                                },
                                "AudioDescriptions": [
                                    {
                                        "CodecSettings": {
                                            "Codec": "AAC",
                                            "AacSettings": {
                                                "Bitrate": 128000,
                                                "CodingMode": "CODING_MODE_2_0",
                                                "SampleRate": 48000
                                            }
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "Inputs": [
                    {
                        "FileInput": f"s3://{bucket_name}/{object_key}"
                    }
                ]
            }
        }
        
        # MediaConvert 작업 시작
        job_id = str(uuid.uuid4())
        response = mediaconvert_client.create_job(
            Role=MEDIACONVERT_ROLE_ARN,
            Settings=job_settings['Settings'],
            Queue='Default'
        )
        
        print(f"MediaConvert job started: {response['Job']['Id']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Video conversion job started successfully',
                'jobId': response['Job']['Id'],
                'inputFile': f"s3://{bucket_name}/{object_key}",
                'outputBucket': OUTPUT_BUCKET
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
