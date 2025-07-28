import json
import boto3
import os
from urllib.parse import unquote_plus

def lambda_handler(event, context):
    """
    변환된 비디오 파일이 S3에 저장되면 Step Functions 워크플로우를 시작하는 Lambda 함수
    """
    
    # 환경 변수
    STEP_FUNCTION_ARN = os.environ['STEP_FUNCTION_ARN']
    
    # AWS 클라이언트 초기화
    stepfunctions = boto3.client('stepfunctions', region_name='ap-northeast-2')
    
    try:
        # EventBridge에서 온 이벤트 파싱
        bucket_name = event['detail']['bucket']['name']
        object_key = unquote_plus(event['detail']['object']['key'])
        
        print(f"Processing converted file: s3://{bucket_name}/{object_key}")
        
        # 파일명에서 정보 추출
        filename = os.path.basename(object_key)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # Step Functions 입력 데이터 준비
        step_input = {
            "detail": {
                "jobId": f"job-{filename_without_ext}",
                "title": filename_without_ext,
                "outputBucket": bucket_name,
                "s3Path": f"s3://{bucket_name}/{object_key}",
                "prefix": "converted/",
                "mediaFormat": "mp4",
                "languageCode": "ko-KR",
                "bucket_path": f"{bucket_name}/{object_key}",
                "originalFilename": filename
            }
        }
        
        # Step Functions 실행 시작
        response = stepfunctions.start_execution(
            stateMachineArn=STEP_FUNCTION_ARN,
            name=f"video-processing-{filename_without_ext}-{context.aws_request_id}",
            input=json.dumps(step_input)
        )
        
        print(f"Step Functions execution started: {response['executionArn']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Step Functions execution started successfully',
                'executionArn': response['executionArn'],
                'inputFile': f"s3://{bucket_name}/{object_key}"
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
