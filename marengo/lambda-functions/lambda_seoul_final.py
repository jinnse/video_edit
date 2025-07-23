import json
import boto3
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    서울 리전에서 TwelveLabs Marengo Embed 최종 테스트
    """
    
    try:
        # 서울 리전 클라이언트
        bedrock_client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
        s3_client = boto3.client('s3', region_name='ap-northeast-2')
        
        # 요청 데이터 파싱
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        object_key = body.get('object_key', 'MXhiZEJnMXFFcW9fMTA4MHA_out_720p.mp4')
        text_query = body.get('text_query', '')
        
        bucket_name = 'videoai340'
        model_id = "twelvelabs.marengo-embed-2-7-v1:0"
        
        # S3 URI
        s3_uri = f"s3://{bucket_name}/{object_key}"
        
        # S3 객체 확인
        try:
            head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
            file_size_mb = head_response['ContentLength'] / (1024 * 1024)
            print(f"S3 파일 확인됨: {object_key}, 크기: {file_size_mb:.2f}MB")
        except Exception as s3_error:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': f'S3 파일 없음: {str(s3_error)}',
                    'bucket': bucket_name,
                    'object_key': object_key
                }, ensure_ascii=False)
            }
        
        # 여러 API 형식 시도
        api_formats = [
            # 형식 1: AWS 문서 기본 형식
            {
                "inputVideo": {
                    "s3Location": {
                        "uri": s3_uri
                    }
                }
            },
            # 형식 2: 간단한 형식
            {
                "video": {
                    "s3Location": {
                        "uri": s3_uri
                    }
                }
            },
            # 형식 3: 최소 형식
            {
                "video_url": s3_uri
            }
        ]
        
        # 각 형식 시도
        for i, request_body in enumerate(api_formats):
            if text_query:
                if i == 0:  # 첫 번째 형식
                    request_body["inputText"] = text_query
                else:  # 다른 형식들
                    request_body["text"] = text_query
            
            try:
                print(f"서울 리전 형식 {i+1} 시도:")
                print(json.dumps(request_body, indent=2, ensure_ascii=False))
                
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
                        'region': 'ap-northeast-2',
                        'api_format': i + 1,
                        'embedding': response_body.get('embedding', []),
                        'embedding_length': len(response_body.get('embedding', [])),
                        'model': model_id,
                        'bucket': bucket_name,
                        'object_key': object_key,
                        'file_size_mb': round(file_size_mb, 2),
                        'response': response_body
                    }, ensure_ascii=False, default=str)
                }
                
            except Exception as format_error:
                error_msg = str(format_error)
                print(f"형식 {i+1} 실패: {error_msg}")
                
                # 특정 오류 분석
                if "doesn't support the model" in error_msg:
                    print("모델 지원 오류 - Model Access 문제일 수 있음")
                elif "ValidationException" in error_msg:
                    print("API 형식 오류")
                elif "AccessDeniedException" in error_msg:
                    print("권한 오류")
                
                continue
        
        # 모든 형식 실패
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': '서울 리전에서 모든 API 형식 실패',
                'region': 'ap-northeast-2',
                'model_id': model_id,
                'bucket': bucket_name,
                'object_key': object_key,
                'file_size_mb': round(file_size_mb, 2),
                'tried_formats': len(api_formats),
                'note': 'Model Access가 활성화되어 있다면 API 형식 문제일 수 있습니다.'
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Lambda 오류: {str(e)}',
                'region': 'ap-northeast-2'
            }, ensure_ascii=False)
        }
