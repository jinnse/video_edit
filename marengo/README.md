# VideoAI340 - TwelveLabs Video Embedding Project

AWS Bedrock TwelveLabs Marengo Embed v2.7 모델을 사용한 비디오 임베딩 생성 프로젝트

## 📁 프로젝트 구조

```
videoai340-project/
├── README.md                    # 프로젝트 문서
├── DEPLOYMENT_GUIDE.md         # 배포 가이드
├── lambda-functions/            # Lambda 함수들
│   ├── lambda_videoai340.py     # 원본 Lambda 함수
│   ├── lambda_simple_test.py    # 간단한 테스트 함수
│   ├── lambda_converse_test.py  # Converse API 테스트
│   ├── lambda_twelvelabs_correct.py  # TwelveLabs 정확한 형식
│   ├── lambda_marengo_official.py    # AWS 공식 문서 기반
│   ├── lambda_marengo_us_east.py     # US East 1 리전용
│   └── lambda_seoul_final.py    # 서울 리전 최종 버전
├── iam-policies/               # IAM 정책들
│   └── lambda-policy.json      # Lambda 실행 정책
└── documentation/              # 문서들
    └── API_REFERENCE.md        # API 참조 문서
```

## 🎯 프로젝트 개요

### 주요 기능
- **S3 비디오 파일 처리**: 최대 2GB 크기의 비디오 파일 지원
- **TwelveLabs Marengo Embed**: 1024차원 비디오 임베딩 생성
- **API Gateway 연동**: RESTful API 제공
- **Cross-Region 지원**: 서울/US East 1 리전 지원

### 기술 스택
- **AWS Lambda**: 서버리스 컴퓨팅
- **AWS Bedrock**: TwelveLabs Marengo Embed v2.7 모델
- **Amazon S3**: 비디오 파일 저장소
- **API Gateway**: REST API 엔드포인트
- **IAM**: 권한 관리

## 🚀 배포된 리소스

### AWS 리소스
- **S3 버킷**: `videoai340` (ap-northeast-2)
- **Lambda 함수**: `videoai340-bedrock-embedding`
- **API Gateway**: `https://vqwo8pof9b.execute-api.ap-northeast-2.amazonaws.com/prod/embed`
- **IAM 역할**: `videoai340-lambda-role`
- **IAM 정책**: `videoai340-lambda-policy`

### Lambda 함수 설정
- **런타임**: Python 3.11
- **메모리**: 10,240 MB (10GB)
- **타임아웃**: 900초 (15분)
- **임시 저장소**: 10,240 MB (10GB)

## 📊 현재 상태

### ✅ 완료된 작업
1. **인프라 구축**: 모든 AWS 리소스 배포 완료
2. **파일 크기 지원**: 2GB까지 처리 가능
3. **API 구현**: AWS 공식 문서 기반 TwelveLabs API 구현
4. **권한 설정**: 서울/US East 1 리전 권한 설정
5. **S3 연동**: 455MB 테스트 비디오 파일 준비

### ⚠️ 해결 필요
- **Model Access**: TwelveLabs 모델 접근 권한 활성화 필요
- **지역별 지원**: 서울 리전에서 Model Access 확인 필요

## 🔧 사용 방법

### API 호출 예시
```bash
curl -X POST https://vqwo8pof9b.execute-api.ap-northeast-2.amazonaws.com/prod/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "object_key": "MXhiZEJnMXFFcW9fMTA4MHA_out_720p.mp4",
    "text_query": "Analyze this video content"
  }'
```

### 응답 형식
```json
{
  "success": true,
  "region": "ap-northeast-2",
  "embedding": [0.1, 0.2, ...],
  "embedding_length": 1024,
  "model": "twelvelabs.marengo-embed-2-7-v1:0",
  "bucket": "videoai340",
  "object_key": "video.mp4",
  "file_size_mb": 455.57
}
```

## 🛠️ 문제 해결

### Model Access 활성화
1. AWS 콘솔 → Amazon Bedrock
2. Model Access 메뉴
3. TwelveLabs → Marengo Embed v2.7
4. Request Access 클릭

### 지역별 설정
- **서울 리전**: ap-northeast-2 (기본)
- **US East 1**: us-east-1 (대안)

## 📝 개발 히스토리

1. **초기 구축**: 기본 Lambda 함수 및 API Gateway 설정
2. **파일 크기 확장**: 100MB → 2GB 지원
3. **API 형식 최적화**: AWS 공식 문서 기반 구현
4. **Cross-Region 지원**: 서울/US East 1 리전 지원
5. **권한 최적화**: IAM 정책 세밀 조정

## 🔗 관련 링크

- [AWS Bedrock TwelveLabs 문서](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-marengo.html)
- [TwelveLabs Marengo Embed 모델](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids-arns.html)

---

**프로젝트 완료일**: 2025-07-23  
**최종 상태**: Model Access 활성화 대기 중
