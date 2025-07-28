# 🚀 AWS Video Processing Pipeline - SAM 배포 패키지

이 패키지는 AWS SAM (Serverless Application Model)을 사용하여 비디오 처리 파이프라인을 한 번에 배포할 수 있도록 구성되었습니다.

## 📁 프로젝트 구조

```
sam-deployment/
├── template.yaml              # SAM 템플릿 파일 (메인)
├── lambda/                    # Lambda 함수 코드
│   ├── video_conversion.py    # 비디오 변환 Lambda
│   ├── start_step_function.py # Step Functions 시작 Lambda
│   ├── transcribe.py          # AWS Transcribe Lambda
│   ├── twelvlabs.py          # Twelvlabs AI 분석 Lambda
│   └── requirements.txt       # Python 의존성
├── stepfunctions/
│   └── workflow.json         # Step Functions 워크플로우 정의
├── scripts/
│   ├── deploy.sh             # 배포 스크립트
│   └── cleanup.sh            # 정리 스크립트
└── docs/
    └── README.md             # 이 가이드 파일
```

## 🏗️ 아키텍처 개요

```
S3 입력 버킷 → EventBridge → Lambda(비디오 변환) → MediaConvert → S3 출력 버킷
    ↓
EventBridge → Lambda(Step Functions 시작) → Step Functions → 병렬 AI 분석
    ↓
TranscribeLambda + TwelvlabsLambda (병렬 실행)
```

### 생성되는 AWS 리소스

- **S3 버킷 (2개)**: 입력/출력 버킷
- **Lambda 함수 (4개)**: 비디오 변환, Step Functions 시작, Transcribe, Twelvlabs
- **IAM 역할 (5개)**: 각 서비스별 권한 관리
- **Step Functions (1개)**: AI 분석 병렬 처리 워크플로우
- **EventBridge 규칙 (2개)**: S3 이벤트 기반 트리거
- **SQS 큐 (1개)**: Dead Letter Queue

## 🔧 사전 요구사항

### 1. 필수 도구 설치

```bash
# AWS CLI 설치 확인
aws --version

# SAM CLI 설치 확인
sam --version
```

### 2. AWS 자격 증명 설정

```bash
aws configure
# 또는 환경 변수 설정
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=ap-northeast-2
```

### 3. 필요한 권한

배포하는 IAM 사용자/역할에 다음 권한이 필요합니다:
- CloudFormation 전체 권한
- IAM 역할 생성/수정 권한
- Lambda, S3, Step Functions, EventBridge, SQS, MediaConvert 권한

## 🚀 배포 방법

### 방법 1: 자동 배포 스크립트 사용 (권장)

```bash
# sam-deployment 디렉토리로 이동
cd sam-deployment

# 배포 스크립트 실행
./scripts/deploy.sh
```

### 방법 2: 수동 배포

```bash
# 1. SAM 빌드
sam build

# 2. SAM 배포 (가이드 모드)
sam deploy --guided

# 또는 직접 파라미터 지정
sam deploy \
    --stack-name video-processing-pipeline \
    --region ap-northeast-2 \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        DateSuffix=20250724 \
        TwelvlabsApiKey=your-api-key
```

## 🧪 테스트 방법

### 1. 비디오 파일 업로드

```bash
# 입력 버킷에 비디오 파일 업로드
aws s3 cp sample-video.mp4 s3://video-input-pipeline-20250724/

# 지원 형식: .mp4, .mov, .avi, .mkv, .wmv, .flv, .webm, .m4v
```

### 2. 처리 과정 모니터링

```bash
# CloudWatch Logs 실시간 모니터링
aws logs tail /aws/lambda/video-conversion-lambda --follow
aws logs tail /aws/lambda/StartStepFunctionLambda --follow
aws logs tail /aws/lambda/TranscribeLambda --follow
aws logs tail /aws/lambda/TwelvlabsLambda --follow
```

### 3. 결과 확인

```bash
# 출력 버킷 내용 확인
aws s3 ls s3://video-output-pipeline-20250724/ --recursive

# 변환된 비디오: converted/
# Transcribe 결과: transcriptions/
# Twelvlabs 분석: twelvlabs-analysis/
```

## 📊 모니터링 및 로그

### CloudWatch 대시보드
- Lambda 함수 실행 메트릭
- Step Functions 실행 상태
- S3 버킷 객체 수
- 오류율 및 지연시간

### Step Functions 콘솔
AWS 콘솔 → Step Functions → VideoProcessingWorkflow에서 실행 상태 확인

## 🔧 설정 변경

### Twelvlabs API 키 업데이트

```bash
# Lambda 환경 변수 업데이트
aws lambda update-function-configuration \
    --function-name TwelvlabsLambda \
    --environment Variables='{TWELVLABS_API_KEY=your-new-api-key}'
```

### 날짜 접미사 변경

template.yaml의 Parameters 섹션에서 DateSuffix 기본값 수정 또는 배포 시 파라미터로 전달

## 🧹 리소스 정리

### 자동 정리 (권장)

```bash
./scripts/cleanup.sh
```

### 수동 정리

```bash
# S3 버킷 내용 삭제
aws s3 rm s3://video-input-pipeline-20250724 --recursive
aws s3 rm s3://video-output-pipeline-20250724 --recursive

# CloudFormation 스택 삭제
aws cloudformation delete-stack --stack-name video-processing-pipeline
```

## 💰 예상 비용 (월간, 100개 비디오 기준)

- **Lambda**: $5-10
- **MediaConvert**: $20-50
- **S3**: $5-15
- **Transcribe**: $10-20
- **Step Functions**: $1-3
- **EventBridge**: $1 미만

## 🔐 보안 고려사항

1. **IAM 권한 최소화**: 각 Lambda 함수에 필요한 최소 권한만 부여
2. **S3 버킷 보안**: 퍼블릭 액세스 차단, 암호화 활성화
3. **API 키 관리**: AWS Systems Manager Parameter Store 사용 권장

## 🚨 문제 해결

### 일반적인 문제

1. **배포 실패**: CloudFormation 이벤트 로그 확인
2. **Lambda 실행 실패**: CloudWatch Logs 확인
3. **MediaConvert 작업 실패**: MediaConvert 콘솔에서 작업 상태 확인
4. **Step Functions 실행 실패**: Step Functions 콘솔에서 실행 히스토리 확인

### 로그 확인 명령어

```bash
# CloudFormation 스택 이벤트
aws cloudformation describe-stack-events --stack-name video-processing-pipeline

# Lambda 함수 로그
aws logs describe-log-streams --log-group-name /aws/lambda/video-conversion-lambda

# MediaConvert 작업 목록
aws mediaconvert list-jobs --region ap-northeast-2
```

## 📞 지원

### 유용한 링크
- [AWS SAM 문서](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS MediaConvert 문서](https://docs.aws.amazon.com/mediaconvert/)
- [AWS Step Functions 문서](https://docs.aws.amazon.com/step-functions/)

### 문제 발생 시
1. CloudWatch Logs 확인
2. AWS 콘솔에서 각 서비스 상태 확인
3. GitHub Issues에 문제 보고

---

## 🎉 완료!

이제 `./scripts/deploy.sh` 명령어 하나로 전체 AWS 비디오 처리 파이프라인을 배포할 수 있습니다!

### 다음 단계
1. 비디오 파일 업로드 테스트
2. 처리 결과 확인
3. 필요에 따라 설정 조정
4. 프로덕션 환경 최적화
