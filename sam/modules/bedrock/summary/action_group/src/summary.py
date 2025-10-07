import json
import boto3
import re
import os

region = os.getenv("AWS_REGION")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # 입력에서 동영상 경로 추출
        input_text = event.get('inputText', '')
        video_path = extract_video_path(input_text)

        print(f"Extracted video path: {video_path}")

        # S3 설정
        bucket_name = 'video-output-pipeline-20250724'
        file_key = 'transcribe/soccer.json'

        # S3에서 JSON 파일 원본만 가져오기
        transcript_data = get_transcript_from_s3(bucket_name, file_key)

        if not transcript_data:
            return create_error_response(event, "전사 파일을 불러올 수 없습니다.")

        print("Successfully loaded transcript data")

        # 분석 결과와 동영상 경로를 함께 포함한 응답 데이터 생성
        response_data = {
            "transcript_data": transcript_data,
            "video_path": video_path,
            "source_bucket": "video-input-pipeline-20250724",  # input 버킷 명시
            "analysis_type": "transcribe"
        }

        # JSON 형태로 포맷하여 반환
        formatted_data = json.dumps(response_data, ensure_ascii=False, separators=(',', ':'))

        return create_success_response(event, formatted_data)

    except Exception as e:
        print(f"Error: {str(e)}")
        return create_error_response(event, f"파일 로드 중 오류가 발생했습니다: {str(e)}")

def extract_video_path(input_text):
    """입력 텍스트에서 동영상 경로 추출 (original/ prefix 보장)"""
    try:
        # 1) JSON 형식에서 video_input 추출 시도
        json_match = re.search(r'\{.*?"video_input".*?\}', input_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            video_input = data.get("video_input", "")
            if video_input:
                print(f"✅ JSON에서 video_input 감지: {video_input}")
                return ensure_original_prefix(video_input)

        # 2) s3 URI 패턴 찾기
        s3_match = re.search(r's3://([^/\s]+)/([^\s"\'<>]+)', input_text)
        if s3_match:
            bucket = s3_match.group(1)
            key = s3_match.group(2)
            print(f"✅ s3 URI 감지: s3://{bucket}/{key}")
            return ensure_original_prefix(key)

        # 3) 파일 경로 패턴 찾기
        path_match = re.search(r'([^\s"\'<>]*\.(mp4|mov|avi|mkv|webm))', input_text, re.IGNORECASE)
        if path_match:
            file_path = path_match.group(1)
            print(f"✅ 파일 경로 감지: {file_path}")
            return ensure_original_prefix(file_path)

        # 4) 단순 파일명 찾기 (확장자 없이)
        simple_match = re.search(r'\b(soccer|video|movie)\b', input_text, re.IGNORECASE)
        if simple_match:
            filename = simple_match.group(1) + ".mp4"
            print(f"✅ 단순 파일명 감지: {filename}")
            return ensure_original_prefix(filename)

        # 5) 기본값 반환
        print("⚠️ 동영상 경로를 찾을 수 없어 기본값 사용")
        return "original/soccer.mp4"

    except Exception as e:
        print(f"⚠️ 동영상 경로 추출 실패: {e}")
        return "original/soccer.mp4"

def ensure_original_prefix(file_path):
    """파일 경로에 original/ prefix가 있는지 확인하고 없으면 추가"""
    if not file_path:
        return "original/soccer.mp4"

    # 이미 경로가 포함된 경우 (/, original/, input/ 등)
    if "/" in file_path:
        # original/로 시작하지 않으면 original/ 추가
        if not file_path.startswith("original/"):
            # 다른 prefix 제거하고 original/ 추가
            filename = file_path.split("/")[-1]  # 마지막 파일명만 추출
            return f"original/{filename}"
        return file_path
    else:
        # 파일명만 있는 경우 original/ prefix 추가
        return f"original/{file_path}"

def get_transcript_from_s3(bucket, key):
    """S3에서 JSON 파일 원본 데이터만 가져오기"""
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        data = response['Body'].read().decode('utf-8')
        transcript_json = json.loads(data)
        return transcript_json
    except Exception as e:
        print(f"Error loading S3 object: {e}")
        return None

def create_success_response(event, data):
    """성공 응답 생성"""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get('actionGroup', 'default'),
            "function": event.get('function', 'default'),
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": data
                    }
                }
            }
        }
    }

def create_error_response(event, error_message):
    """에러 응답 생성"""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get('actionGroup', 'default'),
            "function": event.get('function', 'default'),
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": error_message
                    }
                }
            }
        }
    }