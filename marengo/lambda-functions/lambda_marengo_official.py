import json
import boto3
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS 공식 문서 기반 TwelveLabs Marengo Embed API 사용
    """
    
    try:
        # AWS 클라이언트 초기화
        bedrock_client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
        
        # 요청 데이터 파싱
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        object_key = body.get('object_key', 'MXhiZEJnMXFFcW9fMTA4MHA_out_720p.mp4')
        text_query = body.get('text_query', '')
        
        bucket_name = 'videoai340'
        model_id = "twelvelabs.marengo-embed-2-7-v1:0"
        
        # S3 URI 생성
        s3_uri = f"s3://{bucket_name}/{object_key}"
        
        # AWS 공식 문서에 따른 TwelveLabs Marengo 요청 형식
        request_body = {
            "inputVideo": {
                "s3Location": {
                    "uri": s3_uri
                }
            }
        }
        
        # 텍스트 쿼리가 있는 경우 추가
        if text_query:
            request_body["inputText"] = text_query
        
        print(f"공식 API 형식 사용: {json.dumps(request_body, indent=2)}")
        
        try:
            # Bedrock Runtime으로 모델 호출
            response = bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )
            
            # 응답 파싱
            response_body = json.loads(response['body'].read())
            print(f"성공적인 응답: {response_body}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'method': 'official_aws_docs',
                    'embedding': response_body.get('embedding', []),
                    'model': model_id,
                    'bucket': bucket_name,
                    'object_key': object_key,
                    's3_uri': s3_uri,
                    'response': response_body
                }, ensure_ascii=False, default=str)
            }
            
        except Exception as invoke_error:
            error_msg = str(invoke_error)
            print(f"Invoke Model 오류: {error_msg}")
            
            # 특정 오류 유형별 처리
            if "ValidationException" in error_msg:
                if "doesn't support the model" in error_msg:
                    return {
                        'statusCode': 400,
                        'body': json.dumps({
                            'error': 'TwelveLabs 모델이 현재 계정/지역에서 지원되지 않음',
                            'details': 'AWS 콘솔에서 Bedrock > Model Access에서 TwelveLabs 모델 접근 권한을 요청해야 할 수 있습니다.',
                            'model_id': model_id,
                            'region': 'ap-northeast-2',
                            'bucket': bucket_name,
                            'object_key': object_key,
                            'original_error': error_msg
                        }, ensure_ascii=False)
                    }
                else:
                    return {
                        'statusCode': 400,
                        'body': json.dumps({
                            'error': 'API 요청 형식 오류',
                            'details': 'TwelveLabs Marengo 모델의 요청 형식이 올바르지 않을 수 있습니다.',
                            'used_format': request_body,
                            'original_error': error_msg
                        }, ensure_ascii=False)
                    }
            elif "AccessDeniedException" in error_msg:
                return {
                    'statusCode': 403,
                    'body': json.dumps({
                        'error': 'TwelveLabs 모델 접근 권한 없음',
                        'details': 'IAM 정책에 TwelveLabs 모델 접근 권한이 없거나 Model Access가 활성화되지 않았습니다.',
                        'model_id': model_id,
                        'original_error': error_msg
                    }, ensure_ascii=False)
                }
            else:
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': '예상치 못한 Bedrock 오류',
                        'model_id': model_id,
                        'original_error': error_msg
                    }, ensure_ascii=False)
                }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Lambda 함수 오류: {str(e)}',
                'bucket': 'videoai340'
            }, ensure_ascii=False)
        }
