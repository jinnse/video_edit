# 🚀 AWS 비디오 처리 파이프라인 배포 순서

이 가이드는 AWS 콘솔에서 리소스를 생성하는 정확한 순서를 제공합니다.

## ⚠️ 배포 전 준비사항

### 1. 환경 정보 확인
- **AWS 리전**: `ap-northeast-2` (서울)
- **AWS 계정 ID**: 콘솔에서 확인 (우측 상단 계정 정보)
- **날짜 접미사**: `20250724` (원하는 날짜로 변경 가능)

### 2. 필요한 서비스 권한
- IAM 역할 생성 권한
- S3 버킷 생성 권한
- Lambda 함수 생성 권한
- Step Functions 생성 권한
- EventBridge 규칙 생성 권한
- SQS 큐 생성 권한

---

## 📋 배포 순서 (반드시 순서대로 진행)

### 1단계: S3 버킷 생성 ⏱️ 5분
📁 **폴더**: `s3/README.md` 참조

**생성할 리소스**:
- `video-input-pipeline-20250724` (입력 버킷)
- `video-output-pipeline-20250724` (출력 버킷)

**중요사항**:
- 두 버킷 모두 EventBridge 알림 활성화 필수
- 리전: ap-northeast-2

---

### 2단계: IAM 역할 생성 ⏱️ 15분
📁 **폴더**: `iam/README.md` 참조

**생성 순서**:
1. `MediaConvertServiceRole`
2. `VideoConversionLambdaRole`
3. `StartStepFunctionLambdaRole`
4. `AIAnalysisLambdaRole`
5. `VideoProcessingStepFunctionsRole`
6. `EventBridgeInvokeLambdaRole`

**중요사항**:
- 인라인 정책의 계정 ID를 실제 계정 ID로 변경
- 각 역할의 신뢰 관계 확인

---

### 3단계: SQS 큐 생성 ⏱️ 3분
📁 **폴더**: `sqs/README.md` 참조

**생성할 리소스**:
- `start_lambda_sqs` (Dead Letter Queue)

**중요사항**:
- 액세스 정책에서 계정 ID 변경

---

### 4단계: Lambda 함수 생성 ⏱️ 20분
📁 **폴더**: `lambda/README.md` 참조

**생성 순서**:
1. `video-conversion-lambda`
2. `StartStepFunctionLambda`
3. `TranscribeLambda`
4. `TwelvlabsLamda`

**중요사항**:
- 각 함수의 실행 역할 정확히 설정
- 환경 변수 설정 (특히 계정 ID)
- 함수 코드에서 YOUR_ACCOUNT_ID 변경

---

### 5단계: Step Functions 생성 ⏱️ 5분
📁 **폴더**: `stepfunctions/README.md` 참조

**생성할 리소스**:
- `VideoProcessingWorkflow`

**중요사항**:
- JSON 정의에서 계정 ID 변경
- Lambda 함수 ARN 확인
- 실행 역할 설정

---

### 6단계: EventBridge 규칙 생성 ⏱️ 10분
📁 **폴더**: `eventbridge/README.md` 참조

**생성 순서**:
1. `S3VideoUploadRule`
2. `call_step`

**중요사항**:
- 이벤트 패턴의 버킷 이름 확인
- Lambda 함수 대상 설정
- Dead Letter Queue 설정 (call_step)

---

## ✅ 배포 완료 후 확인사항

### 1. 리소스 생성 확인
- [ ] S3 버킷 2개 생성됨
- [ ] IAM 역할 6개 생성됨
- [ ] SQS 큐 1개 생성됨
- [ ] Lambda 함수 4개 생성됨
- [ ] Step Functions 1개 생성됨
- [ ] EventBridge 규칙 2개 생성됨

### 2. 연결 상태 확인
- [ ] S3 버킷 EventBridge 알림 활성화
- [ ] EventBridge 규칙 → Lambda 함수 연결
- [ ] Lambda 함수 → Step Functions 연결
- [ ] Step Functions → Lambda 함수들 연결

### 3. 권한 확인
- [ ] 각 Lambda 함수의 실행 역할 설정
- [ ] IAM 역할의 정책 연결 상태
- [ ] EventBridge 실행 역할 설정

---

## 🧪 전체 시스템 테스트

### 1. 엔드투엔드 테스트
1. **입력 버킷에 비디오 파일 업로드**:
   ```
   video-input-pipeline-20250724/test-video.mp4
   ```

2. **처리 과정 모니터링**:
   - EventBridge 규칙 실행 확인
   - video-conversion-lambda 로그 확인
   - MediaConvert 작업 상태 확인
   - 출력 버킷에 변환된 파일 생성 확인
   - call_step 규칙 실행 확인
   - StartStepFunctionLambda 실행 확인
   - Step Functions 워크플로우 실행 확인
   - AI 분석 Lambda 함수들 실행 확인

### 2. 예상 처리 시간
- **비디오 변환**: 2-10분 (파일 크기에 따라)
- **AI 분석**: 1-5분 (병렬 처리)
- **전체 처리**: 3-15분

---

## 📊 모니터링 및 로그 확인

### 1. CloudWatch Logs
- `/aws/lambda/video-conversion-lambda`
- `/aws/lambda/StartStepFunctionLambda`
- `/aws/lambda/TranscribeLambda`
- `/aws/lambda/TwelvlabsLamda`

### 2. AWS 서비스 콘솔
- **MediaConvert**: 작업 상태 확인
- **Step Functions**: 실행 히스토리 확인
- **EventBridge**: 규칙 메트릭 확인
- **SQS**: Dead Letter Queue 메시지 확인

---

## 🚨 문제 해결

### 일반적인 문제와 해결방법

1. **Lambda 함수 실행 실패**
   - CloudWatch Logs에서 오류 메시지 확인
   - IAM 역할 권한 확인
   - 환경 변수 설정 확인

2. **EventBridge 규칙이 트리거되지 않음**
   - S3 버킷 EventBridge 알림 활성화 확인
   - 이벤트 패턴 정확성 확인
   - 파일 확장자 및 경로 확인

3. **Step Functions 실행 실패**
   - 입력 JSON 형식 확인
   - Lambda 함수 ARN 확인
   - 실행 역할 권한 확인

4. **MediaConvert 작업 실패**
   - 입력 파일 형식 확인
   - MediaConvert 서비스 역할 권한 확인
   - 출력 버킷 권한 확인

---

## 🧹 리소스 정리

테스트 완료 후 비용 절약을 위해 다음 순서로 리소스를 삭제하세요:

1. EventBridge 규칙 삭제
2. Step Functions 삭제
3. Lambda 함수 삭제
4. SQS 큐 삭제
5. S3 버킷 내용 삭제 후 버킷 삭제
6. IAM 역할 삭제

---

## 💡 추가 개선사항

1. **알림 설정**: SNS를 통한 처리 완료 알림
2. **오류 처리**: 더 상세한 오류 처리 및 재시도 로직
3. **모니터링**: CloudWatch 대시보드 구성
4. **보안**: 더 세밀한 IAM 권한 설정
5. **비용 최적화**: Lambda 메모리 및 타임아웃 최적화
