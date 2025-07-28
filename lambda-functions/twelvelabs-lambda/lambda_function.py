import boto3
  
import json
  
import time
  
import hashlib
  
import urllib.parse
  

  
client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
  

  
def lambda_handler(event, context):
  
    try:
  
        # 받은 이벤트에서 경로 추출
  
        video_s3_path = event.get('s3Path')  # s3Path s3://버킷이름/파일명.mp4
  
        bucket_path = event.get('bucket_path')  # bucket_path s3://버킷이름

        video_name = event.get('title')
  

  
        sts_client = boto3.client('sts')
  
        account_id = sts_client.get_caller_identity()["Account"] 
  
        print(f'파일 이름 {video_name}, 버킷 경로 {bucket_path}')
        
  
        # 요청 본문 구성
  
        input_body = {
  
                "inputType": "video",
  
                "mediaSource": {
  
                    "s3Location": {
  
                        "uri": video_s3_path,  # 기존 s3Path
  
                        "bucketOwner": account_id
  
                    }
  
                }
  
            }
  

  
        output_body = {
  
                "s3OutputDataConfig": {
  
                    "s3Uri": f"{bucket_path}marengo_data"  # 기존 bucket_path
  
                }
  
            }
  

  
        # 요청 ID 토큰 생성
  
        response = client.start_async_invoke(
  
            clientRequestToken=hashlib.sha256(video_s3_path.encode('utf-8')).hexdigest()[:32],  # 기존 file_key -> video_s3_path
  
            modelId='twelvelabs.marengo-embed-2-7-v1:0',
  
            modelInput=input_body,
  
            outputDataConfig=output_body,
  
            tags=[
  
                {
  
                    'key': 'string',
  
                    'value': 'string'
  
                },
  
            ]
        )
  
    except KeyError as e:
  
        print(f"KeyError: {e}")
  
        print(f"Event structure: {json.dumps(event)}")
  
        return {'statusCode': 400, 'body': f'Missing key: {e}'}
  

  
    except Exception as e:
  
        print(f"Unexpected error: {e}")
  
        return {'statusCode': 500, 'body': f'Error: {e}'}
  