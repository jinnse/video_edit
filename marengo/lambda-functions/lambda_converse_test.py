import json
import boto3
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    TwelveLabs 모델을 Converse API로 테스트
    """
    
    try:
        # AWS 클라이언트 초기화
        bedrock_client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
        
        # 요청 데이터 파싱
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        object_key = body.get('object_key', 'MXhiZEJnMXFFcW9fMTA4MHA_out_720p.mp4')
        text_query = body.get('text_query', 'Analyze this video and describe what you see.')
        
        bucket_name = 'videoai340'
        model_id = "twelvelabs.marengo-embed-2-7-v1:0"
        
        # S3 URI 생성
        s3_uri = f"s3://{bucket_name}/{object_key}"
        
        try:
            # Converse API 사용
            response = bedrock_client.converse(
                modelId=model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "video": {
                                    "format": "mp4",
                                    "source": {
                                        "s3Location": {
                                            "uri": s3_uri
                                        }
                                    }
                                }
                            },
                            {
                                "text": text_query
                            }
                        ]
                    }
                ]
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'method': 'converse_api',
                    'response': response,
                    'model': model_id,
                    'bucket': bucket_name,
                    'object_key': object_key
                }, ensure_ascii=False, default=str)
            }
            
        except Exception as converse_error:
            print(f"Converse API 실패: {str(converse_error)}")
            
            # 대안: 직접 invoke_model with different approach
            try:
                # TwelveLabs embedding 전용 형식
                request_body = {
                    "video": s3_uri,
                    "text": text_query
                }
                
                response = bedrock_client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body),
                    contentType='application/json',
                    accept='application/json'
                )
                
                response_body = json.loads(response['body'].read())
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'success': True,
                        'method': 'invoke_model_simple',
                        'embedding': response_body.get('embedding', []),
                        'model': model_id,
                        'bucket': bucket_name,
                        'object_key': object_key
                    }, ensure_ascii=False)
                }
                
            except Exception as invoke_error:
                print(f"Invoke Model 실패: {str(invoke_error)}")
                
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'TwelveLabs 모델 호출 실패',
                        'converse_error': str(converse_error),
                        'invoke_error': str(invoke_error),
                        'bucket': bucket_name,
                        'object_key': object_key,
                        'model': model_id
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
