import json
import boto3
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    US East 1 지역에서 TwelveLabs Marengo Embed API 사용
    """
    
    try:
        # AWS 클라이언트 초기화 - US East 1 사용
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        s3_client = boto3.client('s3', region_name='ap-northeast-2')  # S3는 여전히 서울
        
        # 요청 데이터 파싱
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        object_key = body.get('object_key', 'MXhiZEJnMXFFcW9fMTA4MHA_out_720p.mp4')
        text_query = body.get('text_query', '')
        
        bucket_name = 'videoai340'
        model_id = "twelvelabs.marengo-embed-2-7-v1:0"
        
        # Cross-region S3 URI (서울 버킷을 US East 1에서 접근)
        s3_uri = f"s3://{bucket_name}/{object_key}"
        
        # S3 객체 존재 확인
        try:
            s3_client.head_object(Bucket=bucket_name, Key=object_key)
            print(f"S3 객체 확인됨: {s3_uri}")
        except Exception as s3_error:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': f'S3 객체를 찾을 수 없음: {str(s3_error)}',
                    'bucket': bucket_name,
                    'object_key': object_key
                }, ensure_ascii=False)
            }
        
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
        
        print(f"US East 1에서 TwelveLabs API 호출: {json.dumps(request_body, indent=2)}")
        
        try:
            # US East 1에서 Bedrock Runtime으로 모델 호출
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
                    'region': 'us-east-1',
                    'embedding': response_body.get('embedding', []),
                    'embedding_dimensions': len(response_body.get('embedding', [])),
                    'model': model_id,
                    'bucket': bucket_name,
                    'object_key': object_key,
                    's3_uri': s3_uri,
                    'response': response_body
                }, ensure_ascii=False, default=str)
            }
            
        except Exception as invoke_error:
            error_msg = str(invoke_error)
            print(f"US East 1 Invoke Model 오류: {error_msg}")
            
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'US East 1에서도 TwelveLabs 모델 호출 실패',
                    'region': 'us-east-1',
                    'model_id': model_id,
                    'bucket': bucket_name,
                    'object_key': object_key,
                    'original_error': error_msg,
                    'suggestion': 'Model Access 권한이 필요할 수 있습니다.'
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
