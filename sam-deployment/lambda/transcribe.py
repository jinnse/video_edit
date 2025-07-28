import json
import boto3
import uuid
import time
import os

def lambda_handler(event, context):
    """
    AWS Transcribe를 사용하여 비디오 파일의 음성을 텍스트로 변환하는 Lambda 함수
    """
    
    # AWS 클라이언트 초기화
    transcribe = boto3.client('transcribe', region_name='ap-northeast-2')
    s3 = boto3.client('s3', region_name='ap-northeast-2')
    
    try:
        # Step Functions에서 전달된 데이터 파싱
        prepared_data = event.get('prepared', {})
        s3_path = prepared_data.get('s3Path', '')
        language_code = prepared_data.get('languageCode', 'ko-KR')
        job_id = prepared_data.get('jobId', str(uuid.uuid4()))
        output_bucket = prepared_data.get('outputBucket', '')
        
        print(f"Starting transcription for: {s3_path}")
        
        # Transcribe 작업 이름 생성
        job_name = f"transcribe-job-{job_id}-{int(time.time())}"
        
        # Transcribe 작업 시작
        response = transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={
                'MediaFileUri': s3_path
            },
            MediaFormat='mp4',
            LanguageCode=language_code,
            OutputBucketName=output_bucket,
            OutputKey=f'transcriptions/{job_name}.json',
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 5,
                'ShowAlternatives': True,
                'MaxAlternatives': 3
            }
        )
        
        print(f"Transcription job started: {job_name}")
        
        # 작업 완료 대기 (최대 10분)
        max_wait_time = 600  # 10분
        wait_interval = 30   # 30초마다 확인
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            job_status = transcribe.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            status = job_status['TranscriptionJob']['TranscriptionJobStatus']
            
            if status == 'COMPLETED':
                transcript_uri = job_status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                print(f"Transcription completed: {transcript_uri}")
                
                return {
                    'statusCode': 200,
                    'transcriptionJobName': job_name,
                    'transcriptUri': transcript_uri,
                    'status': 'COMPLETED',
                    'message': 'Transcription completed successfully'
                }
            elif status == 'FAILED':
                failure_reason = job_status['TranscriptionJob'].get('FailureReason', 'Unknown error')
                print(f"Transcription failed: {failure_reason}")
                
                return {
                    'statusCode': 500,
                    'transcriptionJobName': job_name,
                    'status': 'FAILED',
                    'error': failure_reason
                }
            
            # 대기
            time.sleep(wait_interval)
            elapsed_time += wait_interval
            print(f"Transcription in progress... ({elapsed_time}s elapsed)")
        
        # 타임아웃
        print(f"Transcription job timeout after {max_wait_time} seconds")
        return {
            'statusCode': 202,
            'transcriptionJobName': job_name,
            'status': 'IN_PROGRESS',
            'message': f'Transcription job is still in progress after {max_wait_time} seconds'
        }
        
    except Exception as e:
        print(f"Error in transcription: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Transcription failed'
        }
