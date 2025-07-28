# Step Functions 생성 가이드

## 🔄 생성할 Step Functions

1. **VideoProcessingWorkflow** - 비디오 AI 분석 병렬 처리 워크플로우

---

## 🔧 AWS 콘솔에서 생성 방법

### 1. AWS Step Functions 콘솔 접속
- AWS 콘솔 → Step Functions 서비스 선택

### 2. VideoProcessingWorkflow 생성

#### 2-1. 상태 머신 생성 시작
1. **"상태 머신 생성"** 클릭
2. **템플릿 선택**: 빈 상태 머신으로 시작
3. **유형**: 표준

#### 2-2. 상태 머신 정의
**정의** 섹션에 다음 JSON 입력:

```json
{
  "Comment": "영상 변환 후 AI 분석 병렬 처리",
  "StartAt": "ExtractVideoInfo",
  "States": {
    "ExtractVideoInfo": {
      "Type": "Pass",
      "Parameters": {
        "jobId.$": "$.detail.jobId",
        "title.$": "$.detail.title",
        "outputBucket.$": "$.detail.outputBucket",
        "s3Path.$": "$.detail.s3Path",
        "prefix.$": "$.detail.prefix",
        "mediaFormat.$": "$.detail.mediaFormat",
        "languageCode.$": "$.detail.languageCode",
        "bucket_path.$": "$.detail.bucket_path",
        "originalFilename.$": "$.detail.originalFilename"
      },
      "ResultPath": "$.prepared",
      "Next": "ParallelAnalysis"
    },
    "ParallelAnalysis": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "Transcribe",
          "States": {
            "Transcribe": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:ap-northeast-2:YOUR_ACCOUNT_ID:function:TranscribeLambda",
              "Parameters": {
                "jobId.$": "$.prepared.jobId",
                "outputBucket.$": "$.prepared.outputBucket",
                "prefix.$": "$.prepared.prefix",
                "mediaFormat.$": "$.prepared.mediaFormat",
                "languageCode.$": "$.prepared.languageCode",
                "title.$": "$.prepared.title"
              },
              "End": true
            }
          }
        },
        {
          "StartAt": "Twelvelabs",
          "States": {
            "Twelvelabs": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:ap-northeast-2:YOUR_ACCOUNT_ID:function:TwelvlabsLamda",
              "Parameters": {
                "jobId.$": "$.prepared.jobId",
                "s3Path.$": "$.prepared.s3Path",
                "bucket_path.$": "$.prepared.bucket_path",
                "originalFilename.$": "$.prepared.originalFilename",
                "title.$": "$.prepared.title"
              },
              "End": true
            }
          }
        }
      ],
      "End": true
    }
  }
}
```

#### 2-3. 상태 머신 설정
1. **상태 머신 이름**: `VideoProcessingWorkflow`
2. **실행 역할**: 기존 역할 선택 → `VideoProcessingStepFunctionsRole`

#### 2-4. 로깅 설정 (선택사항)
- **로그 수준**: OFF (또는 ERROR/ALL)
- **실행 데이터 포함**: 비활성화

#### 2-5. 추적 설정 (선택사항)
- **X-Ray 추적**: 비활성화

#### 2-6. 태그 설정 (선택사항)
- **키**: `Project`
- **값**: `VideoProcessingPipeline`

#### 2-7. 상태 머신 생성
1. **"상태 머신 생성"** 클릭
2. 생성 완료 후 ARN 확인: `arn:aws:states:ap-northeast-2:YOUR_ACCOUNT_ID:stateMachine:VideoProcessingWorkflow`

---

## 📊 워크플로우 구조 설명

### 1. ExtractVideoInfo (Pass State)
- **목적**: 입력 데이터를 정리하고 다음 단계에서 사용할 형태로 변환
- **입력**: EventBridge에서 전달된 이벤트 데이터
- **출력**: 정리된 비디오 정보 ($.prepared 경로에 저장)

### 2. ParallelAnalysis (Parallel State)
- **목적**: 두 개의 AI 분석 작업을 병렬로 실행
- **브랜치 1**: Transcribe (음성 → 텍스트 변환)
- **브랜치 2**: Twelvelabs (비디오 AI 분석)

#### 브랜치 1: Transcribe
- **Lambda 함수**: TranscribeLambda
- **작업**: Amazon Transcribe를 사용한 음성 인식
- **입력**: 변환된 비디오 파일 정보
- **출력**: 음성 인식 작업 상태

#### 브랜치 2: Twelvelabs
- **Lambda 함수**: TwelvlabsLamda
- **작업**: Twelvelabs API를 사용한 비디오 분석
- **입력**: 원본 비디오 파일 정보
- **출력**: 비디오 분석 결과

---

## 🔍 테스트 방법

### 1. 수동 실행 테스트
1. **Step Functions 콘솔**에서 상태 머신 선택
2. **"실행 시작"** 클릭
3. **실행 이름**: `test-execution-1`
4. **입력 JSON**:

```json
{
  "detail": {
    "jobId": "test-job-123",
    "title": "sample_video",
    "outputBucket": "video-output-pipeline-20250724",
    "s3Path": "s3://video-output-pipeline-20250724/converted/sample_video_converted.mp4",
    "prefix": "converted/",
    "mediaFormat": "mp4",
    "languageCode": "ko-KR",
    "bucket_path": "video-output-pipeline-20250724/converted/sample_video_converted.mp4",
    "originalFilename": "sample_video.mp4"
  }
}
```

5. **"실행 시작"** 클릭

### 2. 실행 결과 확인
- **실행 상태**: SUCCEEDED/FAILED/RUNNING
- **각 단계별 입력/출력 데이터 확인**
- **실행 시간 및 비용 확인**

---

## ✅ 확인 사항

- [ ] VideoProcessingWorkflow 상태 머신 생성 완료
- [ ] YOUR_ACCOUNT_ID를 실제 계정 ID로 변경
- [ ] Lambda 함수 ARN이 올바른지 확인
- [ ] 실행 역할이 올바르게 설정됨
- [ ] 테스트 실행이 성공적으로 완료됨

---

## 📝 참고사항

- YOUR_ACCOUNT_ID를 실제 AWS 계정 ID로 변경하세요
- Lambda 함수들이 먼저 생성되어 있어야 합니다
- 상태 머신 이름은 정확히 `VideoProcessingWorkflow`로 설정하세요
- 병렬 처리로 인해 두 Lambda 함수가 동시에 실행됩니다
- 실행 역할에 Lambda 함수 호출 권한이 있는지 확인하세요

---

## 🚨 문제 해결

### 일반적인 오류
1. **Lambda 함수를 찾을 수 없음**: ARN이 올바른지 확인
2. **권한 부족**: 실행 역할에 Lambda 호출 권한 확인
3. **입력 데이터 오류**: JSON 형식과 필수 필드 확인
4. **타임아웃**: Lambda 함수의 제한 시간 설정 확인
