import json
import boto3
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    간단한 TwelveLabs 모델 테스트
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
        
        # 여러 가지 API 형식 시도
        api_formats = [
            # 형식 1
            {
                "video": {
                    "s3Location": {
                        "uri": s3_uri
                    }
                }
            },
            # 형식 2
            {
                "inputVideo": {
                    "s3Location": {
                        "uri": s3_uri
                    }
                }
            },
            # 형식 3
            {
                "video_url": s3_uri
            },
            # 형식 4
            {
                "input": {
                    "video": {
                        "s3_uri": s3_uri
                    }
                }
            }
        ]
        
        # 각 형식을 순차적으로 시도
        for i, request_body in enumerate(api_formats):
            try:
                if text_query:
                    if "text" not in request_body:
                        request_body["text"] = text_query
                
                print(f"시도 {i+1}: {json.dumps(request_body, indent=2)}")
                
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
                        'api_format_used': i + 1,
                        'embedding': response_body.get('embedding', []),
                        'model': model_id,
                        'bucket': bucket_name,
                        'object_key': object_key,
                        'file_size_mb': 455.57
                    }, ensure_ascii=False)
                }
                
            except Exception as format_error:
                print(f"형식 {i+1} 실패: {str(format_error)}")
                continue
        
        # 모든 형식이 실패한 경우
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': '모든 API 형식 시도 실패',
                'bucket': bucket_name,
                'object_key': object_key,
                'tried_formats': len(api_formats)
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
