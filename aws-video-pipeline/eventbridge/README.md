# EventBridge 규칙 생성 가이드

## 📡 생성할 EventBridge 규칙

1. **S3VideoUploadRule** - 입력 버킷의 비디오 파일 업로드 감지
2. **call_step** - 출력 버킷의 변환된 파일 감지

---

## 🔧 AWS 콘솔에서 생성 방법

### 1. AWS EventBridge 콘솔 접속
- AWS 콘솔 → EventBridge 서비스 선택 → **규칙** 메뉴

---

### 2. S3VideoUploadRule 생성

#### 2-1. 규칙 생성 시작
1. **"규칙 생성"** 클릭
2. **이벤트 버스**: default

#### 2-2. 규칙 세부 정보
- **이름**: `S3VideoUploadRule`
- **설명**: `입력 버킷에 비디오 파일 업로드 시 Lambda 함수 실행`
- **이벤트 패턴**: 선택

#### 2-3. 이벤트 패턴 정의
**이벤트 소스**: AWS 서비스
**AWS 서비스**: S3
**이벤트 유형**: Object Created

**사용자 지정 패턴 (JSON 편집기)**를 선택하고 다음 패턴 입력:

```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": {
      "name": ["video-input-pipeline-20250724"]
    },
    "object": {
      "key": [
        {
          "suffix": ".mp4"
        },
        {
          "suffix": ".mov"
        },
        {
          "suffix": ".avi"
        },
        {
          "suffix": ".mkv"
        },
        {
          "suffix": ".wmv"
        },
        {
          "suffix": ".flv"
        },
        {
          "suffix": ".webm"
        },
        {
          "suffix": ".m4v"
        }
      ]
    }
  }
}
```

#### 2-4. 대상 설정
1. **대상 유형**: AWS 서비스
2. **대상 선택**: Lambda 함수
3. **함수**: `video-conversion-lambda`

#### 2-5. 추가 설정
- **실행 역할**: 새 역할 생성 (자동) 또는 기존 역할 사용
- **Dead Letter Queue**: 사용 안 함
- **재시도 정책**: 기본값 (최대 재시도 횟수: 185, 최대 보존 기간: 24시간)

#### 2-6. 태그 (선택사항)
- **키**: `Project`
- **값**: `VideoProcessingPipeline`

#### 2-7. 규칙 생성
**"규칙 생성"** 클릭

---

### 3. call_step 규칙 생성

#### 3-1. 규칙 생성 시작
1. **"규칙 생성"** 클릭
2. **이벤트 버스**: default

#### 3-2. 규칙 세부 정보
- **이름**: `call_step`
- **설명**: `stepfunction을 부르는 규칙`
- **이벤트 패턴**: 선택

#### 3-3. 이벤트 패턴 정의
**사용자 지정 패턴 (JSON 편집기)**를 선택하고 다음 패턴 입력:

```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": {
      "name": ["video-output-pipeline-20250724"]
    },
    "object": {
      "key": [
        {
          "prefix": "converted/"
        }
      ]
    }
  }
}
```

#### 3-4. 대상 설정
1. **대상 유형**: AWS 서비스
2. **대상 선택**: Lambda 함수
3. **함수**: `StartStepFunctionLambda`

#### 3-5. 추가 설정
**실행 역할**: 새 역할 생성 또는 기존 역할 사용

**Dead Letter Queue 설정**:
1. **Dead Letter Queue 사용**: 활성화
2. **대상**: SQS 큐
3. **큐**: `start_lambda_sqs`

**재시도 정책**:
- **최대 재시도 횟수**: 3
- **최대 보존 기간**: 1시간

#### 3-6. 태그 (선택사항)
- **키**: `Project`
- **값**: `VideoProcessingPipeline`

#### 3-7. 규칙 생성
**"규칙 생성"** 클릭

---

## 🔍 이벤트 패턴 설명

### S3VideoUploadRule 패턴
```json
{
  "source": ["aws.s3"],                    // S3 서비스에서 발생한 이벤트
  "detail-type": ["Object Created"],       // 객체 생성 이벤트
  "detail": {
    "bucket": {
      "name": ["video-input-pipeline-20250724"]  // 특정 입력 버킷
    },
    "object": {
      "key": [                             // 파일 확장자 필터링
        {"suffix": ".mp4"},
        {"suffix": ".mov"},
        // ... 기타 비디오 형식
      ]
    }
  }
}
```

### call_step 패턴
```json
{
  "source": ["aws.s3"],                    // S3 서비스에서 발생한 이벤트
  "detail-type": ["Object Created"],       // 객체 생성 이벤트
  "detail": {
    "bucket": {
      "name": ["video-output-pipeline-20250724"]  // 특정 출력 버킷
    },
    "object": {
      "key": [
        {"prefix": "converted/"}           // converted/ 폴더의 파일만
      ]
    }
  }
}
```

---

## 🧪 테스트 방법

### 1. S3VideoUploadRule 테스트
1. **입력 버킷**에 비디오 파일 업로드:
   ```
   video-input-pipeline-20250724/test-video.mp4
   ```

2. **EventBridge 콘솔**에서 규칙 메트릭 확인
3. **Lambda 함수 로그** 확인 (CloudWatch Logs)
4. **MediaConvert 작업** 상태 확인

### 2. call_step 테스트
1. **출력 버킷의 converted/ 폴더**에 파일 업로드:
   ```
   video-output-pipeline-20250724/converted/test_converted.mp4
   ```

2. **EventBridge 콘솔**에서 규칙 메트릭 확인
3. **StartStepFunctionLambda 로그** 확인
4. **Step Functions 실행** 상태 확인

---

## ✅ 확인 사항

- [ ] S3VideoUploadRule 생성 완료
- [ ] call_step 규칙 생성 완료
- [ ] 버킷 이름이 실제 버킷과 일치
- [ ] Lambda 함수 대상 설정 완료
- [ ] Dead Letter Queue 설정 완료 (call_step)
- [ ] 테스트 실행 성공

---

## 📊 모니터링

### EventBridge 메트릭 (CloudWatch)
- **MatchedEvents**: 패턴과 일치한 이벤트 수
- **SuccessfulInvocations**: 성공한 대상 호출 수
- **FailedInvocations**: 실패한 대상 호출 수

### 확인 방법
1. **EventBridge 콘솔** → **규칙** → 규칙 선택
2. **모니터링** 탭에서 메트릭 확인
3. **CloudWatch**에서 상세 메트릭 확인

---

## 📝 참고사항

- 버킷 이름을 실제 생성한 버킷 이름으로 변경하세요
- S3 버킷에 EventBridge 알림이 활성화되어 있어야 합니다
- 이벤트 패턴은 대소문자를 구분합니다
- Lambda 함수가 먼저 생성되어 있어야 합니다
- Dead Letter Queue는 실패한 이벤트 디버깅에 유용합니다

---

## 🚨 문제 해결

### 일반적인 문제
1. **이벤트가 트리거되지 않음**
   - S3 버킷의 EventBridge 알림 활성화 확인
   - 이벤트 패턴의 버킷 이름 확인
   - 파일 확장자가 패턴과 일치하는지 확인

2. **Lambda 함수 실행 실패**
   - Lambda 함수 권한 확인
   - EventBridge 실행 역할 권한 확인
   - Dead Letter Queue에서 실패 메시지 확인

3. **권한 오류**
   - EventBridge 서비스 역할 확인
   - Lambda 함수 실행 역할 확인
   - S3 버킷 정책 확인
