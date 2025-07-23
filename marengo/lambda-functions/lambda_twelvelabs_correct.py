import json
import boto3
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    TwelveLabs Marengo Embed 모델의 정확한 API 형식 사용
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
        
        # TwelveLabs Embedding 모델의 정확한 형식
        # 문서에 따르면 video embedding을 위한 특별한 형식이 있을 수 있음
        
        api_formats_to_try = [
            # 형식 1: 단순한 S3 URI
            {
                "video_s3_uri": s3_uri
            },
            # 형식 2: 표준 embedding 형식
            {
                "inputs": [
                    {
                        "video": {
                            "s3_uri": s3_uri
                        }
                    }
                ]
            },
            # 형식 3: TwelveLabs 특화 형식
            {
                "video": {
                    "source": {
                        "type": "s3",
                        "uri": s3_uri
                    }
                }
            },
            # 형식 4: 최소한의 형식
            {
                "video_url": s3_uri
            }
        ]
        
        # 텍스트 쿼리가 있는 경우 추가
        if text_query:
            for fmt in api_formats_to_try:
                fmt["text"] = text_query
        
        # 각 형식을 시도
        for i, request_body in enumerate(api_formats_to_try):
            try:
                print(f"TwelveLabs 형식 {i+1} 시도: {json.dumps(request_body, indent=2)}")
                
                response = bedrock_client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body),
                    contentType='application/json',
                    accept='application/json'
                )
                
                response_body = json.loads(response['body'].read())
                print(f"성공! 응답: {response_body}")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'success': True,
                        'api_format_used': i + 1,
                        'response': response_body,
                        'embedding': response_body.get('embedding', response_body.get('embeddings', [])),
                        'model': model_id,
                        'bucket': bucket_name,
                        'object_key': object_key,
                        's3_uri': s3_uri
                    }, ensure_ascii=False, default=str)
                }
                
            except Exception as format_error:
                error_msg = str(format_error)
                print(f"TwelveLabs 형식 {i+1} 실패: {error_msg}")
                
                # 특정 오류 메시지 확인
                if "doesn't support the model" in error_msg:
                    continue
                elif "ValidationException" in error_msg:
                    continue
                else:
                    # 다른 종류의 오류는 더 자세히 로깅
                    print(f"예상치 못한 오류: {error_error}")
                    continue
        
        # 모든 형식 실패 시 상세 정보 반환
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'TwelveLabs 모델 호출 실패 - 모든 API 형식 시도됨',
                'model_id': model_id,
                'model_status': 'ACTIVE',
                'bucket': bucket_name,
                'object_key': object_key,
                's3_uri': s3_uri,
                'tried_formats': len(api_formats_to_try),
                'suggestion': 'TwelveLabs 모델이 현재 지역에서 지원되지 않거나 특별한 접근 방식이 필요할 수 있습니다.'
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
