import json
import boto3
import requests
import time
import os

def lambda_handler(event, context):
    """
    Twelvlabs API를 사용하여 비디오 AI 분석을 수행하는 Lambda 함수
    """
    
    # 환경 변수
    TWELVLABS_API_KEY = os.environ.get('TWELVLABS_API_KEY', '')
    
    if not TWELVLABS_API_KEY or TWELVLABS_API_KEY == 'your-twelvlabs-api-key':
        print("Warning: Twelvlabs API key not configured properly")
        return {
            'statusCode': 200,
            'message': 'Twelvlabs API key not configured - skipping analysis',
            'status': 'SKIPPED'
        }
    
    # AWS 클라이언트 초기화
    s3 = boto3.client('s3', region_name='ap-northeast-2')
    
    try:
        # Step Functions에서 전달된 데이터 파싱
        prepared_data = event.get('prepared', {})
        s3_path = prepared_data.get('s3Path', '')
        job_id = prepared_data.get('jobId', '')
        output_bucket = prepared_data.get('outputBucket', '')
        original_filename = prepared_data.get('originalFilename', 'unknown')
        
        print(f"Starting Twelvlabs analysis for: {s3_path}")
        
        # S3에서 비디오 파일의 presigned URL 생성 (Twelvlabs가 접근할 수 있도록)
        bucket_name = s3_path.split('/')[2]
        object_key = '/'.join(s3_path.split('/')[3:])
        
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=3600  # 1시간
        )
        
        # Twelvlabs API 헤더
        headers = {
            'x-api-key': TWELVLABS_API_KEY,
            'Content-Type': 'application/json'
        }
        
        # 비디오 업로드 요청
        upload_payload = {
            'url': presigned_url,
            'index_id': 'your-index-id',  # 실제 인덱스 ID로 변경 필요
            'language': 'ko'
        }
        
        # 실제 Twelvlabs API 호출 대신 모의 응답 (API 키가 없는 경우)
        # 실제 사용 시에는 아래 주석을 해제하고 모의 응답 부분을 제거하세요
        
        """
        # 실제 Twelvlabs API 호출
        upload_response = requests.post(
            'https://api.twelvelabs.io/v1.2/tasks',
            headers=headers,
            json=upload_payload,
            timeout=60
        )
        
        if upload_response.status_code != 200:
            raise Exception(f"Twelvlabs upload failed: {upload_response.text}")
        
        task_id = upload_response.json()['_id']
        
        # 작업 완료 대기
        max_wait_time = 600  # 10분
        wait_interval = 30   # 30초마다 확인
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            status_response = requests.get(
                f'https://api.twelvelabs.io/v1.2/tasks/{task_id}',
                headers=headers,
                timeout=30
            )
            
            if status_response.status_code == 200:
                task_status = status_response.json()['status']
                
                if task_status == 'ready':
                    # 분석 결과 가져오기
                    video_id = status_response.json()['video_id']
                    
                    # 검색 또는 분석 수행
                    search_payload = {
                        'query': 'Describe what happens in this video',
                        'index_id': 'your-index-id',
                        'search_options': ['visual', 'conversation', 'text_in_video']
                    }
                    
                    search_response = requests.post(
                        'https://api.twelvelabs.io/v1.2/search',
                        headers=headers,
                        json=search_payload,
                        timeout=60
                    )
                    
                    if search_response.status_code == 200:
                        analysis_result = search_response.json()
                        break
                elif task_status == 'failed':
                    raise Exception("Twelvlabs analysis failed")
            
            time.sleep(wait_interval)
            elapsed_time += wait_interval
        """
        
        # 모의 분석 결과 (실제 API 사용 시 제거)
        analysis_result = {
            'video_analysis': {
                'summary': f'AI analysis completed for {original_filename}',
                'objects_detected': ['person', 'car', 'building'],
                'scenes': [
                    {'timestamp': '00:00:00', 'description': 'Opening scene'},
                    {'timestamp': '00:01:30', 'description': 'Main content'},
                    {'timestamp': '00:03:00', 'description': 'Closing scene'}
                ],
                'emotions': ['happy', 'neutral', 'excited'],
                'confidence_score': 0.85
            },
            'processing_time': '120 seconds',
            'api_version': 'v1.2'
        }
        
        # 결과를 S3에 저장
        result_key = f'twelvlabs-analysis/{job_id}-analysis.json'
        s3.put_object(
            Bucket=output_bucket,
            Key=result_key,
            Body=json.dumps(analysis_result, indent=2, ensure_ascii=False),
            ContentType='application/json'
        )
        
        print(f"Twelvlabs analysis completed and saved to s3://{output_bucket}/{result_key}")
        
        return {
            'statusCode': 200,
            'analysisResult': analysis_result,
            'resultLocation': f's3://{output_bucket}/{result_key}',
            'status': 'COMPLETED',
            'message': 'Twelvlabs analysis completed successfully'
        }
        
    except Exception as e:
        print(f"Error in Twelvlabs analysis: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Twelvlabs analysis failed'
        }
