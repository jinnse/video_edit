import json
import boto3
import logging

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
stepfunctions_client = boto3.client('stepfunctions')

def lambda_handler(event, context):
    """
    EventBridge에서 호출되어 Step Functions 워크플로우를 시작하는 Lambda 함수
    """
    try:
        logger.info(f"받은 이벤트: {json.dumps(event)}")
        
        # EventBridge 이벤트에서 S3 정보 추출
        detail = event.get('detail', {})
        bucket_name = detail.get('bucket', {}).get('name', '')
        object_key = detail.get('object', {}).get('key', '')
        
        if not bucket_name or not object_key:
            logger.error("S3 버킷 또는 객체 키가 없습니다")
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid S3 event data')
            }
        
        # Step Functions 입력 데이터 준비
        step_input = {
            "detail": {
                "jobId": f"job-{context.aws_request_id}",
                "title": object_key.split('/')[-1],  # 파일명만 추출
                "outputBucket": "video-output-pipeline-20250724",
                "s3Path": f"s3://{bucket_name}/{object_key}",
                "prefix": "converted/",
                "mediaFormat": "mp4",
                "languageCode": "ko-KR",
                "bucket_path": f"{bucket_name}/{object_key}",
                "originalFilename": object_key.split('/')[-1]
            }
        }
        
        # Step Functions 실행
        state_machine_arn = "arn:aws:states:ap-northeast-2:567279714866:stateMachine:VideoProcessingWorkflow"
        
        response = stepfunctions_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=f"execution-{context.aws_request_id}",
            input=json.dumps(step_input)
        )
        
        logger.info(f"Step Functions 실행 시작: {response['executionArn']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Step Functions 워크플로우가 시작되었습니다',
                'executionArn': response['executionArn'],
                'input': step_input
            })
        }
        
    except Exception as e:
        logger.error(f"오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
