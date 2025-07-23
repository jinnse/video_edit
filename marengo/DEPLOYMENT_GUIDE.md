# VideoAI340 배포 가이드

## 🚀 배포 단계별 가이드

### 1단계: AWS 리소스 생성

#### S3 버킷 생성
```bash
aws s3 mb s3://videoai340 --region ap-northeast-2
```

#### IAM 역할 생성
```bash
# 신뢰 정책
aws iam create-role \
    --role-name videoai340-lambda-role \
    --assume-role-policy-document file://trust-policy.json

# 실행 정책 생성
aws iam create-policy \
    --policy-name videoai340-lambda-policy \
    --policy-document file://iam-policies/lambda-policy.json

# 정책 연결
aws iam attach-role-policy \
    --role-name videoai340-lambda-role \
    --policy-arn arn:aws:iam::ACCOUNT_ID:policy/videoai340-lambda-policy
```

### 2단계: Lambda 함수 배포

#### 함수 생성
```bash
# Lambda 함수 생성
aws lambda create-function \
    --function-name videoai340-bedrock-embedding \
    --runtime python3.11 \
    --role arn:aws:iam::ACCOUNT_ID:role/videoai340-lambda-role \
    --handler lambda_seoul_final.lambda_handler \
    --zip-file fileb://lambda-function.zip \
    --timeout 900 \
    --memory-size 10240 \
    --ephemeral-storage Size=10240 \
    --region ap-northeast-2
```

#### 환경 변수 설정
```bash
aws lambda update-function-configuration \
    --function-name videoai340-bedrock-embedding \
    --environment Variables='{S3_BUCKET=videoai340}' \
    --region ap-northeast-2
```

### 3단계: API Gateway 설정

#### REST API 생성
```bash
# API 생성
aws apigateway create-rest-api \
    --name videoai340-api \
    --region ap-northeast-2

# 리소스 및 메서드 생성
# (상세 단계는 AWS 콘솔에서 수행 권장)
```

### 4단계: Model Access 활성화

#### AWS 콘솔에서 설정
1. **Amazon Bedrock 콘솔 접속**
2. **Model Access 메뉴 클릭**
3. **TwelveLabs 섹션 찾기**
4. **Marengo Embed v2.7 모델 활성화**
5. **Request Access 클릭 (필요시)**

#### CLI로 확인
```bash
# 모델 상태 확인
aws bedrock list-foundation-models \
    --region ap-northeast-2 \
    --query 'modelSummaries[?contains(modelId, `twelvelabs`)]'

# 직접 테스트
aws bedrock-runtime invoke-model \
    --model-id "twelvelabs.marengo-embed-2-7-v1:0" \
    --body file://test-request.json \
    --content-type "application/json" \
    --region ap-northeast-2 \
    response.json
```

## 🔧 설정 파일들

### trust-policy.json
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### test-request.json
```json
{
  "inputVideo": {
    "s3Location": {
      "uri": "s3://videoai340/test-video.mp4"
    }
  },
  "inputText": "test embedding"
}
```

## 📊 리소스 사양

### Lambda 함수 설정
- **메모리**: 10,240 MB (최대)
- **타임아웃**: 900초 (15분)
- **임시 저장소**: 10,240 MB
- **런타임**: Python 3.11

### 지원 파일 크기
- **최대 크기**: 2GB (2,048MB)
- **권장 크기**: 500MB 이하
- **테스트 파일**: 455MB

## 🌍 지역별 배포

### 서울 리전 (ap-northeast-2)
- **기본 설정**: 모든 리소스 서울 리전
- **Model Access**: 별도 활성화 필요

### US East 1 (us-east-1)
- **대안 설정**: Bedrock만 US East 1 사용
- **Cross-Region**: S3는 서울, Bedrock은 US East 1

## 🔍 테스트 및 검증

### 기본 테스트
```bash
curl -X POST https://API_GATEWAY_URL/prod/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "object_key": "test-video.mp4",
    "text_query": "test"
  }'
```

### 성공 응답 예시
```json
{
  "success": true,
  "embedding": [0.1, 0.2, ...],
  "embedding_length": 1024,
  "model": "twelvelabs.marengo-embed-2-7-v1:0"
}
```

## 🚨 문제 해결

### 일반적인 오류들

#### "doesn't support the model"
- **원인**: Model Access 미활성화
- **해결**: AWS 콘솔에서 Model Access 활성화

#### "AccessDeniedException"
- **원인**: IAM 권한 부족
- **해결**: IAM 정책 확인 및 업데이트

#### "ValidationException"
- **원인**: API 요청 형식 오류
- **해결**: 요청 형식 확인

### 로그 확인
```bash
# CloudWatch 로그 확인
aws logs tail /aws/lambda/videoai340-bedrock-embedding \
    --follow --region ap-northeast-2
```

## 📝 유지보수

### 정기 점검 항목
1. **Model Access 상태 확인**
2. **IAM 정책 업데이트**
3. **Lambda 함수 성능 모니터링**
4. **S3 버킷 용량 관리**

### 업데이트 절차
1. **코드 수정**
2. **ZIP 파일 생성**
3. **Lambda 함수 업데이트**
4. **테스트 실행**

---

**작성일**: 2025-07-23  
**버전**: 1.0
