# Lambda 함수 생성 가이드

## 🚀 생성할 Lambda 함수

1. **video-conversion-lambda** - 비디오 변환 (MediaConvert)
2. **StartStepFunctionLambda** - Step Functions 워크플로우 시작
3. **TranscribeLambda** - 음성을 텍스트로 변환
4. **TwelvlabsLamda** - 비디오 AI 분석

---

## 🔧 AWS 콘솔에서 생성 방법

### 1. video-conversion-lambda 생성

#### 1-1. 함수 생성
1. **AWS Lambda 콘솔** → **함수 생성**
2. **새로 작성** 선택
3. **함수 이름**: `video-conversion-lambda`
4. **런타임**: Python 3.9
5. **아키텍처**: x86_64
6. **실행 역할**: 기존 역할 사용 → `VideoConversionLambdaRole`
7. **함수 생성** 클릭

#### 1-2. 환경 변수 설정
**구성** → **환경 변수** → **편집**
- `OUTPUT_BUCKET`: `video-output-pipeline-20250724`
- `MEDIACONVERT_ROLE_ARN`: `arn:aws:iam::YOUR_ACCOUNT_ID:role/MediaConvertServiceRole`

#### 1-3. 기본 설정
**구성** → **일반 구성** → **편집**
- **제한 시간**: 5분 0초
- **메모리**: 128MB

#### 1-4. 함수 코드
**코드** 탭에서 다음 코드 입력:

```python
import json
import boto3
import uuid
import os
from urllib.parse import unquote_plus

def lambda_handler(event, context):
    """
    S3에 업로드된 비디오 파일을 MediaConvert를 사용해 변환하는 Lambda 함수
    """
    
    # 환경 변수
    OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
    MEDIACONVERT_ROLE_ARN = os.environ['MEDIACONVERT_ROLE_ARN']
    
    try:
        # EventBridge에서 온 이벤트 파싱
        bucket_name = event['detail']['bucket']['name']
        object_key = unquote_plus(event['detail']['object']['key'])
        
        print(f"Processing file: s3://{bucket_name}/{object_key}")
        
        # MediaConvert 클라이언트 초기화
        mediaconvert = boto3.client('mediaconvert', region_name='ap-northeast-2')
        
        # MediaConvert 엔드포인트 가져오기
        endpoints = mediaconvert.describe_endpoints()
        endpoint_url = endpoints['Endpoints'][0]['Url']
        mediaconvert_client = boto3.client('mediaconvert', endpoint_url=endpoint_url, region_name='ap-northeast-2')
        
        # 파일명에서 확장자 제거
        filename_without_ext = os.path.splitext(os.path.basename(object_key))[0]
        
        # MediaConvert 작업 설정
        job_settings = {
            "Role": MEDIACONVERT_ROLE_ARN,
            "Settings": {
                "OutputGroups": [
                    {
                        "Name": "File Group",
                        "OutputGroupSettings": {
                            "Type": "FILE_GROUP_SETTINGS",
                            "FileGroupSettings": {
                                "Destination": f"s3://{OUTPUT_BUCKET}/converted/"
                            }
                        },
                        "Outputs": [
                            {
                                "NameModifier": f"_{filename_without_ext}_converted",
                                "ContainerSettings": {
                                    "Container": "MP4"
                                },
                                "VideoDescription": {
                                    "CodecSettings": {
                                        "Codec": "H_264",
                                        "H264Settings": {
                                            "RateControlMode": "QVBR",
                                            "QvbrSettings": {
                                                "QvbrQualityLevel": 7
                                            }
                                        }
                                    }
                                },
                                "AudioDescriptions": [
                                    {
                                        "CodecSettings": {
                                            "Codec": "AAC",
                                            "AacSettings": {
                                                "Bitrate": 128000,
                                                "CodingMode": "CODING_MODE_2_0",
                                                "SampleRate": 48000
                                            }
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "Inputs": [
                    {
                        "FileInput": f"s3://{bucket_name}/{object_key}"
                    }
                ]
            }
        }
        
        # MediaConvert 작업 시작
        response = mediaconvert_client.create_job(
            Role=MEDIACONVERT_ROLE_ARN,
            Settings=job_settings['Settings'],
            Queue='Default'
        )
        
        print(f"MediaConvert job started: {response['Job']['Id']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Video conversion job started successfully',
                'jobId': response['Job']['Id'],
                'inputFile': f"s3://{bucket_name}/{object_key}",
                'outputBucket': OUTPUT_BUCKET
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
```

---

### 2. StartStepFunctionLambda 생성

#### 2-1. 함수 생성
1. **함수 이름**: `StartStepFunctionLambda`
2. **런타임**: Python 3.9
3. **실행 역할**: `StartStepFunctionLambdaRole`

#### 2-2. 기본 설정
- **제한 시간**: 3초
- **메모리**: 128MB

#### 2-3. 함수 코드

```python
import json
import boto3
import uuid

def lambda_handler(event, context):
    """
    Step Functions 워크플로우를 시작하는 Lambda 함수
    """
    
    stepfunctions = boto3.client('stepfunctions', region_name='ap-northeast-2')
    
    try:
        # EventBridge에서 온 이벤트 파싱
        bucket_name = event['detail']['bucket']['name']
        object_key = event['detail']['object']['key']
        
        print(f"Starting Step Functions for: s3://{bucket_name}/{object_key}")
        
        # Step Functions 입력 데이터 준비
        step_input = {
            "detail": {
                "jobId": str(uuid.uuid4()),
                "title": object_key.split('/')[-1].split('.')[0],
                "outputBucket": bucket_name,
                "s3Path": f"s3://{bucket_name}/{object_key}",
                "prefix": "converted/",
                "mediaFormat": "mp4",
                "languageCode": "ko-KR",
                "bucket_path": f"{bucket_name}/{object_key}",
                "originalFilename": object_key.split('/')[-1]
            }
        }
        
        # Step Functions 실행
        response = stepfunctions.start_execution(
            stateMachineArn='arn:aws:states:ap-northeast-2:YOUR_ACCOUNT_ID:stateMachine:VideoProcessingWorkflow',
            name=f"execution-{str(uuid.uuid4())}",
            input=json.dumps(step_input)
        )
        
        print(f"Step Functions execution started: {response['executionArn']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Step Functions execution started successfully',
                'executionArn': response['executionArn']
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
```

---

### 3. TranscribeLambda 생성

#### 3-1. 함수 생성
1. **함수 이름**: `TranscribeLambda`
2. **런타임**: Python 3.9
3. **실행 역할**: `AIAnalysisLambdaRole`

#### 3-2. 기본 설정
- **제한 시간**: 5분 0초
- **메모리**: 128MB

#### 3-3. 함수 코드

```python
import json
import boto3
import uuid
import time

def lambda_handler(event, context):
    """
    Amazon Transcribe를 사용해 비디오의 음성을 텍스트로 변환하는 Lambda 함수
    """
    
    transcribe = boto3.client('transcribe', region_name='ap-northeast-2')
    
    try:
        # Step Functions에서 온 입력 파싱
        job_id = event['jobId']
        output_bucket = event['outputBucket']
        title = event['title']
        language_code = event.get('languageCode', 'ko-KR')
        
        # S3 URI 구성
        media_uri = f"s3://{output_bucket}/converted/{title}_converted.mp4"
        
        print(f"Starting transcription for: {media_uri}")
        
        # Transcribe 작업 이름 (고유해야 함)
        job_name = f"transcribe-{job_id}-{int(time.time())}"
        
        # Transcribe 작업 시작
        response = transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={
                'MediaFileUri': media_uri
            },
            MediaFormat='mp4',
            LanguageCode=language_code,
            OutputBucketName=output_bucket,
            OutputKey=f'transcriptions/{title}_transcription.json'
        )
        
        print(f"Transcription job started: {job_name}")
        
        return {
            'statusCode': 200,
            'jobName': job_name,
            'jobId': job_id,
            'title': title,
            'transcriptionStatus': 'IN_PROGRESS',
            'outputLocation': f"s3://{output_bucket}/transcriptions/{title}_transcription.json"
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'jobId': event.get('jobId', 'unknown')
        }
```

---

### 4. TwelvlabsLamda 생성

#### 4-1. 함수 생성
1. **함수 이름**: `TwelvlabsLamda`
2. **런타임**: Python 3.9
3. **실행 역할**: `AIAnalysisLambdaRole`

#### 4-2. 환경 변수 설정
- `TWELVELABS_API_KEY`: `your-twelvelabs-api-key`

#### 4-3. 기본 설정
- **제한 시간**: 3초
- **메모리**: 128MB

#### 4-4. 함수 코드

```python
import json
import os

def lambda_handler(event, context):
    """
    Twelvelabs API를 사용해 비디오를 분석하는 Lambda 함수
    (실제 API 호출은 구현 필요)
    """
    
    try:
        # Step Functions에서 온 입력 파싱
        job_id = event['jobId']
        s3_path = event['s3Path']
        title = event['title']
        original_filename = event['originalFilename']
        
        print(f"Starting Twelvelabs analysis for: {s3_path}")
        
        # Twelvelabs API 키 확인
        api_key = os.environ.get('TWELVELABS_API_KEY')
        if not api_key:
            raise ValueError("TWELVELABS_API_KEY environment variable not set")
        
        # TODO: 실제 Twelvelabs API 호출 구현
        # 현재는 더미 응답 반환
        
        analysis_result = {
            'jobId': job_id,
            'title': title,
            'originalFilename': original_filename,
            'analysisStatus': 'COMPLETED',
            'results': {
                'summary': f'Analysis completed for {title}',
                'tags': ['video', 'analysis'],
                'duration': '00:02:30',
                'scenes': []
            }
        }
        
        print(f"Twelvelabs analysis completed for job: {job_id}")
        
        return {
            'statusCode': 200,
            'body': analysis_result
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'jobId': event.get('jobId', 'unknown')
        }
```

---

## ✅ 확인 사항

- [ ] video-conversion-lambda 생성 및 환경 변수 설정 완료
- [ ] StartStepFunctionLambda 생성 완료 (YOUR_ACCOUNT_ID 수정 필요)
- [ ] TranscribeLambda 생성 완료
- [ ] TwelvlabsLamda 생성 및 API 키 설정 완료

## 📝 참고사항

- YOUR_ACCOUNT_ID를 실제 AWS 계정 ID로 변경하세요
- Twelvelabs API 키는 실제 키로 설정하세요
- 모든 함수는 ap-northeast-2 리전에 생성해야 합니다
- 함수 이름은 정확히 일치해야 합니다 (대소문자 구분)
