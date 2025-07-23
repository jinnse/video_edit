import json
import boto3
import subprocess
import os
import uuid
import tempfile
from urllib.parse import urlparse, parse_qs
import re

def lambda_handler(event, context):
    """
    AWS Lambda function for YouTube video download and processing
    """
    try:
        # CORS 헤더
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
        # OPTIONS 요청 처리 (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # POST 요청 처리
        if event.get('httpMethod') != 'POST':
            return {
                'statusCode': 405,
                'headers': headers,
                'body': json.dumps({'error': 'Method not allowed'})
            }
        
        # 요청 본문 파싱
        body = json.loads(event.get('body', '{}'))
        youtube_url = body.get('url', '').strip()
        
        if not youtube_url:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'YouTube URL이 필요합니다'})
            }
        
        # YouTube URL 유효성 검사
        if not is_valid_youtube_url(youtube_url):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '유효한 YouTube URL을 입력해주세요'})
            }
        
        # YouTube 비디오 다운로드 및 처리
        result = process_youtube_video(youtube_url)
        
        if result['success']:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps(result)
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': f'서버 오류: {str(e)}',
                'suggestion': '잠시 후 다시 시도해주세요.'
            })
        }

def is_valid_youtube_url(url):
    """YouTube URL 유효성 검사"""
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return youtube_regex.match(url) is not None

def process_youtube_video(url):
    """YouTube 비디오 다운로드 및 S3 업로드"""
    try:
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            unique_id = str(uuid.uuid4())
            
            # yt-dlp 설치 및 실행 (Lambda Layer 또는 컨테이너 이미지 필요)
            download_path = os.path.join(temp_dir, f"video_{unique_id}.%(ext)s")
            
            # yt-dlp 명령어 실행
            cmd = [
                '/opt/bin/yt-dlp',  # Lambda Layer에 설치된 yt-dlp 경로
                '--format', 'best[height<=720]',
                '--output', download_path,
                '--no-playlist',
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': '다운로드 실패',
                    'details': result.stderr,
                    'suggestion': '다른 비디오를 시도하거나 잠시 후 다시 시도해주세요.'
                }
            
            # 다운로드된 파일 찾기
            downloaded_files = [f for f in os.listdir(temp_dir) if f.startswith(f"video_{unique_id}")]
            
            if not downloaded_files:
                return {
                    'success': False,
                    'error': '다운로드된 파일을 찾을 수 없습니다'
                }
            
            downloaded_file = os.path.join(temp_dir, downloaded_files[0])
            
            # S3에 업로드
            s3_client = boto3.client('s3')
            bucket_name = os.environ.get('S3_BUCKET_NAME', 'your-video-bucket')
            s3_key = f"downloads/{unique_id}/{downloaded_files[0]}"
            
            s3_client.upload_file(downloaded_file, bucket_name, s3_key)
            
            # 다운로드 URL 생성 (Presigned URL)
            download_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': s3_key},
                ExpiresIn=3600  # 1시간 유효
            )
            
            return {
                'success': True,
                'message': 'YouTube 비디오 다운로드 완료',
                'download_url': download_url,
                'file_name': downloaded_files[0],
                'expires_in': '1시간'
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': '다운로드 시간 초과',
            'suggestion': '더 짧은 비디오를 시도해주세요.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'처리 중 오류: {str(e)}'
        }
