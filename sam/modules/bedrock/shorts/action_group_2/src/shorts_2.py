import boto3
import json
import re
import os
from urllib.parse import urlparse
from botocore.exceptions import ClientError

# 환경변수로 설정 관리
DEFAULT_S3_BUCKET = os.getenv("DEFAULT_S3_BUCKET", "video-input-pipeline-20250724")
DEFAULT_S3_PREFIX = os.getenv("DEFAULT_S3_PREFIX", "original/")  # 👈 방법1 추가
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
PEGASUS_MODEL_ID = os.getenv("PEGASUS_PROFILE", "apac.twelvelabs.pegasus-1-2-v1:0")

bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)

# S3 URI와 HTTPS URL 모두 매칭하는 정규식
S3_REGEX = re.compile(
    r"s3://[a-zA-Z0-9.\-_]+/[a-zA-Z0-9.\-_/]+\.(mp4|mov|mkv|m4v|avi)(?:\?[^\s]*)?",
    re.IGNORECASE
)
HTTPS_REGEX = re.compile(
    r"https://[a-zA-Z0-9.\-_]+\.s3\.[a-zA-Z0-9\-]+\.amazonaws\.com/[a-zA-Z0-9.\-_/]+\.(mp4|mov|mkv|m4v|avi)(?:\?[^\s]*)?",
    re.IGNORECASE
)


def extract_filename_from_url(url_or_text: str) -> str:
    """URL이나 텍스트에서 파일명 추출"""
    try:
        # HTTPS URL 패턴 먼저 확인
        https_match = HTTPS_REGEX.search(url_or_text)
        if https_match:
            parsed_url = urlparse(https_match.group(0))
            filename = parsed_url.path.lstrip('/')  # 앞의 '/' 제거
            print(f"📝 HTTPS URL에서 파일명 추출: {https_match.group(0)} → {filename}")
            return filename

        # S3 URI 패턴 확인
        s3_match = S3_REGEX.search(url_or_text)
        if s3_match:
            s3_uri = s3_match.group(0)
            # s3://bucket/path/file.mp4 → path/file.mp4
            parts = s3_uri[5:].split('/', 1)  # s3:// 제거
            if len(parts) == 2:
                filename = parts[1]  # bucket 이후 경로
                print(f"📝 S3 URI에서 파일명 추출: {s3_uri} → {filename}")
                return filename

        # 직접 파일명인 경우 (cam3.mp4 같은)
        filename_match = re.search(
            r'([a-zA-Z0-9.\-_/]+\.(mp4|mov|mkv|m4v|avi))',
            url_or_text,
            re.IGNORECASE
        )
        if filename_match:
            filename = filename_match.group(1)
            print(f"📝 텍스트에서 파일명 추출: {filename}")
            return filename

        return None
    except Exception as e:
        print(f"❌ 파일명 추출 오류: {e}")
        return None


def build_s3_uri(filename: str, bucket: str = DEFAULT_S3_BUCKET) -> str:
    """파일명과 버킷으로 S3 URI 생성 (prefix 자동 추가)"""
    # prefix 보정: 없으면 추가
    if DEFAULT_S3_PREFIX and not filename.startswith(DEFAULT_S3_PREFIX):
        filename = f"{DEFAULT_S3_PREFIX}{filename}"
    s3_uri = f"s3://{bucket}/{filename}"
    print(f"🔗 S3 URI 생성: {bucket} + {filename} = {s3_uri}")
    return s3_uri

def analyze_video_with_pegasus(video_s3_uri, prompt=""):
    """영상 분석 함수"""
    try:
        sts = boto3.client('sts', region_name=AWS_REGION)
        bucket_owner = sts.get_caller_identity()['Account']
        
        print(f"🔍 분석 시작 - 영상: {video_s3_uri}")
        print(f"👤 계정 ID: {bucket_owner}")
        print(f"💬 프롬프트: {prompt}")
        
        # 동적으로 파일명 추출
        video_filename = video_s3_uri.split('/')[-1] if '/' in video_s3_uri else video_s3_uri
        
        # S3 URI에서 전체 경로 추출 (original/soccer.mp4 형태)
        s3_path = video_s3_uri.replace(f"s3://{DEFAULT_S3_BUCKET}/", "")
        
        payload = {
            "inputPrompt": f"""Find all scenes where: {prompt}

Return each scene with extended timestamps to include complete context.
Include buffer time before and after each scene for smooth playback.

JSON format:
{{
  "scenes": [
    {{
      "prompt": "{prompt}",
      "text": "scene description",
      "start_time": start_seconds,
      "end_time": end_seconds,
      "video_input": "{s3_path}"
    }}
  ]
}}""",
        "mediaSource": {
            "s3Location": {
                "uri": video_s3_uri, 
                "bucketOwner": bucket_owner
            }
        },
        "temperature": 0.1,  # 더 정확한 타임스탬프를 위해 낮춤
        "maxOutputTokens": 3072
    }
        
        response = bedrock_runtime.invoke_model(
            modelId=PEGASUS_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        
        result = json.loads(response['body'].read())
        
        # 결과 상세 로그 추가
        print(f"🔍 받은 결과 타입: {type(result)}")
        print(f"🔍 받은 결과 키들: {list(result.keys()) if isinstance(result, dict) else 'dict가 아님'}")
        print(f"🔍 받은 결과 전체: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # Pegasus 응답 형식 처리
        if isinstance(result, dict) and 'message' in result:
            # message 안의 JSON 문자열을 파싱
            try:
                parsed_message = json.loads(result['message'])
                print(f"🔧 message 내 JSON 파싱 성공: {type(parsed_message)}")
                result = parsed_message  # 파싱된 JSON으로 교체
            except json.JSONDecodeError as e:
                print(f"⚠️ message JSON 파싱 실패: {e}")
                # 파싱 실패 시 원본 message 텍스트 사용
                result = {"error": "JSON 파싱 실패", "raw_message": result['message']}
        
        if not result:
            raise ValueError("빈 응답을 받았습니다")
            
        print(f"🔧 최종 처리된 결과: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print(f"✅ 분석 완료!")
        return result
        
    except Exception as e:
        print(f"❌ Pegasus 호출 오류: {str(e)}")
        raise

def validate_s3_uri(s3_uri: str) -> tuple[bool, str]:
    """S3 URI 유효성 검사"""
    try:
        if not s3_uri.startswith("s3://"):
            return False, "S3 URI가 's3://'로 시작하지 않습니다"
        
        parts = s3_uri[5:].split('/', 1)
        if len(parts) != 2:
            return False, "잘못된 S3 URI 형식입니다"
        
        bucket_name, object_key = parts
        
        if not bucket_name or not object_key:
            return False, "버킷 이름 또는 객체 키가 비어있습니다"
        
        try:
            s3_client.head_object(Bucket=bucket_name, Key=object_key)
            return True, f"✅ S3 파일 확인됨: {bucket_name}/{object_key}"
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False, f"파일이 존재하지 않습니다: {bucket_name}/{object_key}"
            elif error_code == '403':
                return False, f"파일 접근 권한이 없습니다: {bucket_name}/{object_key}"
            else:
                return False, f"S3 오류 ({error_code}): {bucket_name}/{object_key}"
                
    except Exception as e:
        return False, f"S3 URI 검증 중 오류: {str(e)}"

def _get_param(event: dict, name: str):
    """Bedrock Agent 파라미터에서 값 추출"""
    params = event.get("parameters")
    if not params:
        return None
    if isinstance(params, dict):
        return params.get(name)
    if isinstance(params, list):
        for p in params:
            if isinstance(p, dict) and p.get("name") == name:
                return p.get("value") or p.get("valueText") or p.get("text") or p.get("stringValue")
    return None

def clean_prompt_text(text: str, extracted_filename: str = None) -> str:
    """텍스트에서 URL/파일명을 제거하고 순수한 프롬프트만 남김"""
    if not text:
        return ""
    
    clean_text = text
    
    # HTTPS URL 제거
    clean_text = HTTPS_REGEX.sub('', clean_text)
    
    # S3 URI 제거  
    clean_text = S3_REGEX.sub('', clean_text)
    
    # 추출된 파일명 제거
    if extracted_filename:
        clean_text = clean_text.replace(extracted_filename, '')
    
    # 여러 공백을 하나로, 앞뒤 공백 제거
    clean_text = ' '.join(clean_text.split()).strip()
    
    # "에서", "에" 같은 불필요한 조사 정리
    clean_text = re.sub(r'^(에서|에)\s+', '', clean_text)
    
    return clean_text

def _resp_text(action_group: str, function_name: str, msg: str):
    """성공 응답 생성"""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function_name,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": msg
                    }
                }
            }
        }
    }

def _resp_err(action_group: str, function_name: str, msg: str):
    """에러 응답 생성"""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function_name,
            "functionResponse": {
                "responseState": "FAILURE",
                "responseBody": {
                    "TEXT": {
                        "body": f"❌ 에러 발생: {msg[:512]}"
                    }
                }
            }
        }
    }

def lambda_handler(event, context):
    """Lambda 핸들러 - 기본값 제거, 필수 입력"""
    print(f"📥 받은 이벤트: {json.dumps(event, default=str, ensure_ascii=False, indent=2)}")
    
    action_group = event.get("actionGroup") or "pegasus_action_group"
    function_name = event.get("function") or "pegasus"
    input_text = event.get("inputText", "")
    
    print(f"🔍 입력 텍스트: '{input_text}'")

    try:
        # 1) 먼저 텍스트에서 파일명 추출 시도
        print(f"🔍 파일명 추출 시도 중...")
        print(f"🔍 입력 텍스트 상세: '{input_text}'")
        print(f"🔍 입력 텍스트 길이: {len(input_text)}")
        
        extracted_filename = extract_filename_from_url(input_text)
        print(f"🔍 추출된 파일명: {extracted_filename}")
        
        if extracted_filename:
            # 파일명으로 S3 URI 생성
            video_s3_uri = build_s3_uri(extracted_filename)
            print(f"🎯 추출된 파일명으로 S3 URI 생성: {video_s3_uri}")
        else:
            # 2) 파일명이 없으면 파라미터에서 S3 URI 확인
            video_s3_uri = _get_param(event, "video_s3_uri")
            print(f"🔍 파라미터에서 가져온 URI: {video_s3_uri}")
            
            if video_s3_uri:
                print(f"📌 파라미터에서 S3 URI 사용: {video_s3_uri}")
                # 파라미터에서 가져온 경우 파일명 추출
                extracted_filename = video_s3_uri.split('/')[-1] if '/' in video_s3_uri else video_s3_uri
            else:
                # 3) 임시 기본값 사용 (디버깅용)
                print(f"⚠️ 파일명을 찾을 수 없음. 입력 텍스트 다시 확인:")
                print(f"   - 전체 텍스트: '{input_text}'")
                print(f"   - 소문자 변환: '{input_text.lower()}'")
                
                # 더 관대한 파일명 검색
                simple_filename_match = re.search(r'([a-zA-Z0-9.\-_]+\.(mp4|mov|avi|mkv|m4v))', input_text, re.IGNORECASE)
                if simple_filename_match:
                    extracted_filename = simple_filename_match.group(1)
                    video_s3_uri = build_s3_uri(extracted_filename)
                    print(f"🎯 관대한 검색으로 파일명 발견: {extracted_filename}")
                else:
                    error_msg = f"파일명을 찾을 수 없습니다. 입력: '{input_text}'. 예: 'cam3.mp4에서 영상 분석해줘' 또는 'video1.mp4 요약해줘'"
                    print(f"❌ {error_msg}")
                    return _resp_err(action_group, function_name, error_msg)
        
        # 4) S3 URI 검증
        is_valid, validation_msg = validate_s3_uri(video_s3_uri)
        if not is_valid:
            print(f"⚠️ S3 검증 실패: {validation_msg}")
        else:
            print(validation_msg)
        
        # 5) 순수한 프롬프트 추출 (URL/파일명 제거)
        clean_prompt = clean_prompt_text(input_text, extracted_filename)
        print(f"🧹 정제된 프롬프트: '{clean_prompt}'")
        
        # 6) 최종 프롬프트 결정
        if clean_prompt:
            final_prompt = clean_prompt
            print(f"✅ 사용자 프롬프트 사용: '{final_prompt}'")
        else:
            final_prompt = "영상을 분석해주세요"
            print(f"⚠️ 기본 프롬프트 사용")

        # 7) 영상 분석 실행
        result = analyze_video_with_pegasus(video_s3_uri, final_prompt)
        
        # 결과 확인 로그 추가
        print(f"🎬 분석 결과 받음:")
        print(f"  - 결과 타입: {type(result)}")
        print(f"  - 결과 길이: {len(str(result))}")
        if isinstance(result, dict):
            print(f"  - 결과 키들: {list(result.keys())}")

        # 8) 응답 메시지 구성
        # 비디오 파일명 추출 (경로에서 파일명만)
        video_filename = video_s3_uri.split('/')[-1] if '/' in video_s3_uri else video_s3_uri
        
        # JSON 형식으로 깔끔하게 표시
        msg = f"""🎬 영상 분석 완료!

📹 분석 영상: {video_filename}
🔍 검색 요청: "{final_prompt}"

📊 분석 결과:
{json.dumps(result, ensure_ascii=False, indent=2)}

---
✨ Twelve Labs Pegasus로 정밀 분석되었습니다.
"""
        
        response = _resp_text(action_group, function_name, msg)
        print(f"✅ 성공 응답 반환")
        return response

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"💥 에러 발생: {error_msg}")
        
        response = _resp_err(action_group, function_name, error_msg)
        print(f"❌ 에러 응답 반환")
        return response