# SQS 큐 생성 가이드

## 📨 생성할 SQS 큐

1. **start_lambda_sqs** - StartStepFunctionLambda 실패 시 Dead Letter Queue

---

## 🔧 AWS 콘솔에서 생성 방법

### 1. AWS SQS 콘솔 접속
- AWS 콘솔 → SQS 서비스 선택

### 2. start_lambda_sqs 큐 생성

#### 2-1. 큐 생성 시작
1. **"큐 생성"** 클릭

#### 2-2. 기본 설정
- **유형**: 표준
- **이름**: `start_lambda_sqs`

#### 2-3. 구성 설정
- **가시성 제한 시간**: 30초 (기본값)
- **메시지 보존 기간**: 4일 (기본값)
- **전송 지연**: 0초 (기본값)
- **최대 메시지 크기**: 256KB (기본값)
- **메시지 수신 대기 시간**: 0초 (기본값)

#### 2-4. 액세스 정책
**정책 방법**: 기본 (큐 소유자만 액세스)

또는 고급 설정으로 다음 정책 사용:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEventBridgeAccess",
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": [
        "sqs:SendMessage"
      ],
      "Resource": "arn:aws:sqs:ap-northeast-2:YOUR_ACCOUNT_ID:start_lambda_sqs"
    },
    {
      "Sid": "AllowOwnerAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:root"
      },
      "Action": "sqs:*",
      "Resource": "arn:aws:sqs:ap-northeast-2:YOUR_ACCOUNT_ID:start_lambda_sqs"
    }
  ]
}
```

#### 2-5. 암호화
- **서버 측 암호화**: 비활성화 (또는 Amazon SQS 관리형 키 사용)

#### 2-6. Dead Letter Queue
- **Dead Letter Queue 사용**: 비활성화 (이 큐 자체가 DLQ이므로)

#### 2-7. 태그 (선택사항)
- **키**: `Project`
- **값**: `VideoProcessingPipeline`

#### 2-8. 큐 생성
- **"큐 생성"** 클릭

---

## ✅ 확인 사항

- [ ] start_lambda_sqs 큐 생성 완료
- [ ] 큐 URL 확인: `https://sqs.ap-northeast-2.amazonaws.com/YOUR_ACCOUNT_ID/start_lambda_sqs`
- [ ] 액세스 정책 설정 완료

---

## 📝 큐 정보

### start_lambda_sqs
- **목적**: StartStepFunctionLambda 실행 실패 시 메시지 저장
- **사용처**: EventBridge call_step 규칙의 Dead Letter Queue
- **메시지 형식**: EventBridge 이벤트 JSON

### 큐 ARN
```
arn:aws:sqs:ap-northeast-2:YOUR_ACCOUNT_ID:start_lambda_sqs
```

## 🔍 모니터링

SQS 콘솔에서 다음 메트릭을 모니터링할 수 있습니다:
- **사용 가능한 메시지**: 처리 대기 중인 메시지 수
- **진행 중인 메시지**: 현재 처리 중인 메시지 수
- **메시지 수신**: 총 수신된 메시지 수
- **메시지 삭제**: 성공적으로 처리된 메시지 수

## 📝 참고사항

- YOUR_ACCOUNT_ID를 실제 AWS 계정 ID로 변경하세요
- 큐는 ap-northeast-2 리전에 생성해야 합니다
- Dead Letter Queue는 Lambda 함수 실행 실패 시 디버깅에 유용합니다
