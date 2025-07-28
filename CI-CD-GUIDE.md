# AWS 비디오 처리 파이프라인 CI/CD 가이드

현재 AWS 환경에 배포된 비디오 처리 파이프라인의 CI/CD 시스템입니다.

## 🎯 개요

- **목적**: AWS Lambda 함수들의 자동 배포
- **트리거**: `lambda-functions/` 폴더 변경 시 자동 실행
- **배포 방식**: 변경된 함수만 선택적 배포

## 🏗️ 현재 AWS 리소스

### Lambda 함수들
- **TwelvlabsLamda**: TwelveLabs API 연동
- **video-conversion-lambda**: MediaConvert 비디오 변환
- **StartStepFunctionLambda**: Step Functions 워크플로우 시작
- **TranscribeLambda**: Amazon Transcribe 음성 인식
- **RekognitionLambda**: Amazon Rekognition (현재 미사용)

## 🚀 사용 방법

### 자동 배포
```bash
# Lambda 함수 수정
vim lambda-functions/twelvelabs-lambda/lambda_function.py

# Git 푸시
git add .
git commit -m "✨ feature: 함수 업데이트"
git push origin main
```

### 수동 배포
```bash
# 특정 함수만 배포
./scripts/deploy.sh twelvelabs

# 모든 함수 배포
./scripts/deploy.sh all
```

## 🔧 설정 필요사항

GitHub Repository Settings → Secrets에 추가:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

## 📊 모니터링

- **GitHub Actions**: https://github.com/Kosunjo/video_edit/actions
- **AWS Lambda 콘솔**: https://ap-northeast-2.console.aws.amazon.com/lambda/
- **CloudWatch 로그**: 각 Lambda 함수별 로그 그룹

---
**리전**: ap-northeast-2 (서울)
