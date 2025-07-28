import json
import boto3
import logging
import uuid
from datetime import datetime

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
transcribe_client = boto3.client('transcribe')
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Amazon Transcribe를 사용하여 비디오/오디오 파일을 텍스트로 변환
    """
    try:
        logger.info(f"받은 이벤트: {json.dumps(event)}")
        
        # Step Functions에서 전달된 데이터 추출
        job_id = event.get('jobId', str(uuid.uuid4()))
        output_bucket = event.get('outputBucket', 'video-output-pipeline-20250724')
        prefix = event.get('prefix', 'converted/')
        media_format = event.get('mediaFormat', 'mp4')
        language_code = event.get('languageCode', 'ko-KR')
        title = event.get('title', 'unknown')
        
        # S3 URI 구성
        media_uri = f"s3://{output_bucket}/{prefix}{title}"
        output_key = f"transcribe/{title}.json"
        
        logger.info(f"Transcribe 작업 시작: {media_uri}")
        
        # Transcribe 작업 이름 생성
        job_name = f"transcribe-{job_id}-{int(datetime.now().timestamp())}"
        
        # Transcribe 작업 시작
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={
                'MediaFileUri': media_uri
            },
            MediaFormat=media_format,
            LanguageCode=language_code,
            OutputBucketName=output_bucket,
            OutputKey=output_key,
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 5,
                'ShowAlternatives': True,
                'MaxAlternatives': 3
            }
        )
        
        logger.info(f"Transcribe 작업 생성됨: {job_name}")
        
        # 작업 완료 대기 (간단한 폴링)
        import time
        max_wait_time = 300  # 5분
        wait_interval = 10   # 10초
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            job_status = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            status = job_status['TranscriptionJob']['TranscriptionJobStatus']
            logger.info(f"Transcribe 작업 상태: {status}")
            
            if status == 'COMPLETED':
                transcript_uri = job_status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                logger.info(f"Transcribe 완료: {transcript_uri}")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'Transcribe 작업이 완료되었습니다',
                        'jobName': job_name,
                        'transcriptUri': transcript_uri,
                        'outputKey': output_key,
                        'status': status
                    })
                }
            elif status == 'FAILED':
                failure_reason = job_status['TranscriptionJob'].get('FailureReason', 'Unknown error')
                logger.error(f"Transcribe 작업 실패: {failure_reason}")
                raise Exception(f"Transcribe 작업 실패: {failure_reason}")
            
            time.sleep(wait_interval)
            elapsed_time += wait_interval
        
        # 타임아웃
        logger.warning(f"Transcribe 작업 타임아웃: {job_name}")
        return {
            'statusCode': 202,
            'body': json.dumps({
                'message': 'Transcribe 작업이 진행 중입니다',
                'jobName': job_name,
                'status': 'IN_PROGRESS'
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
