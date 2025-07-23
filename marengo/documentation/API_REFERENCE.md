# VideoAI340 API 참조 문서

## 📡 API 엔드포인트

### Base URL
```
https://vqwo8pof9b.execute-api.ap-northeast-2.amazonaws.com/prod
```

## 🎯 비디오 임베딩 생성

### POST /embed

S3에 저장된 비디오 파일로부터 TwelveLabs Marengo Embed v2.7 모델을 사용하여 임베딩을 생성합니다.

#### 요청

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "object_key": "string",     // 필수: S3 객체 키
  "text_query": "string"      // 선택: 텍스트 쿼리
}
```

#### 요청 예시
```bash
curl -X POST https://vqwo8pof9b.execute-api.ap-northeast-2.amazonaws.com/prod/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "object_key": "MXhiZEJnMXFFcW9fMTA4MHA_out_720p.mp4",
    "text_query": "Analyze this video content"
  }'
```

#### 성공 응답 (200)
```json
{
  "success": true,
  "region": "ap-northeast-2",
  "embedding": [0.1, 0.2, 0.3, ...],
  "embedding_length": 1024,
  "model": "twelvelabs.marengo-embed-2-7-v1:0",
  "bucket": "videoai340",
  "object_key": "video.mp4",
  "file_size_mb": 455.57,
  "response": {
    // TwelveLabs 모델 원본 응답
  }
}
```

#### 오류 응답

**400 Bad Request - 잘못된 요청**
```json
{
  "error": "object_key 또는 video_path가 필요합니다",
  "example": {
    "object_key": "videos/sample.mp4",
    "text_query": "선택적 텍스트 쿼리"
  }
}
```

**403 Forbidden - 권한 없음**
```json
{
  "error": "TwelveLabs 모델 접근 권한 없음",
  "details": "IAM 정책에 TwelveLabs 모델 접근 권한이 없거나 Model Access가 활성화되지 않았습니다.",
  "model_id": "twelvelabs.marengo-embed-2-7-v1:0"
}
```

**404 Not Found - 파일 없음**
```json
{
  "error": "S3 파일 없음: NoSuchKey",
  "bucket": "videoai340",
  "object_key": "nonexistent.mp4"
}
```

**413 Payload Too Large - 파일 크기 초과**
```json
{
  "error": "파일이 너무 큽니다: 2500.00MB. 2GB(2048MB) 이하만 지원됩니다."
}
```

**500 Internal Server Error - 서버 오류**
```json
{
  "error": "Lambda 함수 오류: 상세 오류 메시지",
  "bucket": "videoai340"
}
```

## 📋 요청 파라미터 상세

### object_key (필수)
- **타입**: string
- **설명**: S3 버킷 내 비디오 파일의 객체 키
- **예시**: `"videos/sample.mp4"`, `"MXhiZEJnMXFFcW9fMTA4MHA_out_720p.mp4"`
- **제한사항**: 
  - 파일 크기: 최대 2GB
  - 지원 형식: MP4, AVI, MOV, MKV, WEBM

### text_query (선택)
- **타입**: string
- **설명**: 비디오 분석을 위한 텍스트 쿼리
- **예시**: `"Analyze this video content"`, `"What is happening in this video?"`
- **제한사항**: 최대 2,000 토큰

## 🔧 TwelveLabs 모델 사양

### Marengo Embed v2.7
- **모델 ID**: `twelvelabs.marengo-embed-2-7-v1:0`
- **입력 모달리티**: TEXT, IMAGE, SPEECH, VIDEO
- **출력 모달리티**: EMBEDDING
- **임베딩 차원**: 1,024
- **최대 비디오 크기**: 2GB
- **최대 처리 시간**: 2시간

## 🌍 지역별 지원

### 서울 리전 (ap-northeast-2)
- **S3 버킷**: videoai340
- **Lambda 함수**: videoai340-bedrock-embedding
- **Bedrock 모델**: TwelveLabs Marengo Embed v2.7

### US East 1 (us-east-1)
- **대안 설정**: Bedrock 모델만 US East 1 사용
- **Cross-Region**: S3는 서울, Bedrock은 US East 1

## 📊 성능 및 제한사항

### 처리 시간
- **소형 파일** (< 100MB): 30초 - 2분
- **중형 파일** (100MB - 500MB): 2분 - 10분
- **대형 파일** (500MB - 2GB): 10분 - 2시간

### 동시 처리
- **Lambda 동시 실행**: 기본 1,000개 (계정별)
- **Bedrock 모델**: ON_DEMAND 방식

### 비용 예상 (월간)
- **Lambda**: 100회 실행 기준 ~$2
- **Bedrock**: 100회 호출 기준 ~$10
- **S3**: 10GB 저장 기준 ~$0.25
- **API Gateway**: 100회 호출 기준 ~$0.35

## 🔍 디버깅 및 모니터링

### CloudWatch 로그
```bash
# 실시간 로그 확인
aws logs tail /aws/lambda/videoai340-bedrock-embedding \
    --follow --region ap-northeast-2
```

### 상태 확인
```bash
# Lambda 함수 상태
aws lambda get-function \
    --function-name videoai340-bedrock-embedding \
    --region ap-northeast-2

# Bedrock 모델 상태
aws bedrock list-foundation-models \
    --region ap-northeast-2 \
    --query 'modelSummaries[?contains(modelId, `twelvelabs`)]'
```

## 📝 사용 예시

### Python 클라이언트
```python
import requests
import json

url = "https://vqwo8pof9b.execute-api.ap-northeast-2.amazonaws.com/prod/embed"
payload = {
    "object_key": "my-video.mp4",
    "text_query": "Describe the main activities in this video"
}

response = requests.post(url, json=payload)
result = response.json()

if result.get('success'):
    embedding = result['embedding']
    print(f"임베딩 생성 성공: {len(embedding)}차원")
else:
    print(f"오류: {result.get('error')}")
```

### JavaScript 클라이언트
```javascript
const response = await fetch('https://vqwo8pof9b.execute-api.ap-northeast-2.amazonaws.com/prod/embed', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    object_key: 'my-video.mp4',
    text_query: 'Analyze this video'
  })
});

const result = await response.json();
if (result.success) {
  console.log(`임베딩 차원: ${result.embedding_length}`);
} else {
  console.error(`오류: ${result.error}`);
}
```

---

**API 버전**: 1.0  
**최종 업데이트**: 2025-07-23
