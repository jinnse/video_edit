# ⚡ 빠른 시작 가이드

AWS 비디오 처리 파이프라인을 5분 안에 배포하세요!

## 🚀 1단계: 사전 준비 (2분)

```bash
# AWS CLI 및 SAM CLI 설치 확인
aws --version
sam --version

# AWS 자격 증명 확인
aws sts get-caller-identity
```

## 🚀 2단계: 배포 (3분)

```bash
# 프로젝트 디렉토리로 이동
cd sam-deployment

# 자동 배포 실행
./scripts/deploy.sh
```

배포 중 Twelvlabs API 키를 묻는 경우, 없으면 엔터를 눌러 건너뛰세요.

## 🧪 3단계: 테스트

```bash
# 비디오 파일 업로드 (예시)
aws s3 cp your-video.mp4 s3://video-input-pipeline-$(date +%Y%m%d)/

# 처리 과정 모니터링
aws logs tail /aws/lambda/video-conversion-lambda --follow
```

## 📊 4단계: 결과 확인

```bash
# 출력 버킷 확인
aws s3 ls s3://video-output-pipeline-$(date +%Y%m%d)/ --recursive
```

## 🧹 정리

```bash
# 리소스 정리
./scripts/cleanup.sh
```

---

## 🎯 지원 비디오 형식
`.mp4`, `.mov`, `.avi`, `.mkv`, `.wmv`, `.flv`, `.webm`, `.m4v`

## 📋 생성되는 리소스
- S3 버킷 2개 (입력/출력)
- Lambda 함수 4개
- Step Functions 1개
- IAM 역할 5개
- EventBridge 규칙 2개
- SQS 큐 1개

## 💡 문제 해결
- 배포 실패 시: CloudWatch Logs 확인
- 권한 오류 시: IAM 권한 확인
- 자세한 가이드: `docs/README.md` 참조

---

**🎉 완료! 이제 비디오를 업로드하고 자동 처리를 확인해보세요!**
