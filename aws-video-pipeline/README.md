# AWS 비디오 처리 파이프라인 - 콘솔 배포 가이드

이 가이드는 AWS 콘솔에서 직접 리소스를 생성하는 방법을 설명합니다.

## 🏗️ 아키텍처 개요

```
S3 업로드 → EventBridge → Lambda(변환) → S3 출력 → EventBridge → Lambda(Step Functions 시작) → Step Functions → 병렬 AI 분석
```

## 📋 배포 순서

### 1단계: S3 버킷 생성
### 2단계: IAM 역할 생성
### 3단계: SQS 큐 생성
### 4단계: Lambda 함수 생성
### 5단계: Step Functions 생성
### 6단계: EventBridge 규칙 생성

---

## 🚀 상세 배포 가이드

각 폴더의 파일을 참조하여 AWS 콘솔에서 설정하세요.

### 필수 환경 변수
- AWS 리전: `ap-northeast-2`
- 계정 ID: `your-account-id`
- 날짜 접미사: `20250724` (또는 원하는 날짜)

### 지원 비디오 형식
- .mp4, .mov, .avi, .mkv, .wmv, .flv, .webm, .m4v

---

## 📁 폴더별 가이드

- `s3/`: S3 버킷 생성 방법
- `iam/`: IAM 역할 및 정책 생성 방법  
- `sqs/`: SQS 큐 생성 방법
- `lambda/`: Lambda 함수 생성 및 코드
- `stepfunctions/`: Step Functions 워크플로우 정의
- `eventbridge/`: EventBridge 규칙 설정

각 폴더의 README.md 파일을 순서대로 따라하면 완전한 파이프라인을 구축할 수 있습니다.
