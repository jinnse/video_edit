import json
import boto3
import base64
from typing import Dict, Any
import os
from urllib.parse import urlparse

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    videoai340 S3 버킷에서 비디오를 읽어 AWS Bedrock TwelveLabs Marengo Embed 2.7로 임베딩 생성
    """
    
    try:
        # AWS 클라이언트 초기화 (서울 리전)
        bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name='ap-northeast-2'
        )
        s3_client = boto3.client(
            's3',
            region_name='ap-northeast-2'
        )
        
        # 요청 데이터 파싱
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # videoai340 버킷의 객체 키
        object_key = body.get('object_key') or body.get('video_path')
        text_query = body.get('text_query', '')
        
        if not object_key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'object_key 또는 video_path가 필요합니다',
                    'example': {
                        'object_key': 'videos/sample.mp4',
                        'text_query': '선택적 텍스트 쿼리'
                    }
                }, ensure_ascii=False)
            }
        
        # 임베딩 생성
        result = generate_embedding_from_videoai340(
            bedrock_client, s3_client, object_key, text_query
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'bucket': 'videoai340',
                'region': 'ap-northeast-2'
            }, ensure_ascii=False)
        }

def generate_embedding_from_videoai340(bedrock_client, s3_client, object_key: str, text_query: str = '') -> Dict[str, Any]:
    """
    videoai340 S3 버킷에서 비디오 파일을 읽어 임베딩 생성
    """
    
    bucket_name = 'videoai340'
    model_id = "twelvelabs.marengo-embed-2-7-v1:0"
    
    try:
        # 방법 1: S3 URI를 직접 사용
        s3_uri = f"s3://{bucket_name}/{object_key}"
        
        request_body = {
            "video": {
                "s3Location": {
                    "uri": s3_uri
                }
            }
        }
        
        if text_query:
            request_body["inputText"] = text_query
        
        # Bedrock 모델 호출
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        return {
            'success': True,
            'embedding': response_body.get('embedding', []),
            'model': model_id,
            'bucket': bucket_name,
            'object_key': object_key,
            's3_uri': s3_uri,
            'query': text_query,
            'embedding_dimension': len(response_body.get('embedding', [])),
            'metadata': response_body.get('metadata', {}),
            'region': 'ap-northeast-2'
        }
        
    except Exception as e:
        print(f"S3 직접 접근 실패, 파일 다운로드 시도: {str(e)}")
        
        # 방법 2: 파일 다운로드 후 처리
        return generate_embedding_with_download(bedrock_client, s3_client, bucket_name, object_key, text_query)

def generate_embedding_with_download(bedrock_client, s3_client, bucket_name: str, object_key: str, text_query: str = '') -> Dict[str, Any]:
    """
    S3에서 파일을 다운로드하여 임베딩 생성
    """
    
    model_id = "twelvelabs.marengo-embed-2-7-v1:0"
    
    try:
        # S3 객체 정보 확인
        head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        file_size = head_response['ContentLength']
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"파일 크기: {file_size_mb:.2f}MB")
        
        if file_size_mb > 2048:  # 2GB = 2048MB
            raise Exception(f"파일이 너무 큽니다: {file_size_mb:.2f}MB. 2GB(2048MB) 이하만 지원됩니다.")
        
        # S3에서 파일 다운로드
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        video_bytes = response['Body'].read()
        
        # Base64 인코딩
        video_base64 = base64.b64encode(video_bytes).decode('utf-8')
        
        # 파일 형식 추출
        file_format = object_key.split('.')[-1].lower()
        if file_format not in ['mp4', 'avi', 'mov', 'mkv', 'webm']:
            file_format = 'mp4'
        
        request_body = {
            "inputVideo": {
                "format": file_format,
                "source": {
                    "bytes": video_base64
                }
            }
        }
        
        if text_query:
            request_body["inputText"] = text_query
        
        # Bedrock 모델 호출
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        return {
            'success': True,
            'embedding': response_body.get('embedding', []),
            'model': model_id,
            'bucket': bucket_name,
            'object_key': object_key,
            'file_size_mb': round(file_size_mb, 2),
            'file_format': file_format,
            'query': text_query,
            'embedding_dimension': len(response_body.get('embedding', [])),
            'metadata': response_body.get('metadata', {}),
            'processing_method': 'download',
            'region': 'ap-northeast-2'
        }
        
    except Exception as e:
        raise Exception(f"파일 처리 실패: {str(e)}")

def list_videos_in_bucket(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    videoai340 버킷의 비디오 파일 목록 조회
    """
    
    try:
        s3_client = boto3.client('s3', region_name='ap-northeast-2')
        bucket_name = 'videoai340'
        
        # 비디오 파일 확장자
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
        
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        
        video_files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if any(key.lower().endswith(ext) for ext in video_extensions):
                    video_files.append({
                        'key': key,
                        'size_mb': round(obj['Size'] / (1024 * 1024), 2),
                        'last_modified': obj['LastModified'].isoformat()
                    })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'bucket': bucket_name,
                'region': 'ap-northeast-2',
                'video_count': len(video_files),
                'videos': video_files
            }, ensure_ascii=False, default=str)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            }, ensure_ascii=False)
        }
