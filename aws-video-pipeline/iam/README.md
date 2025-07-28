# IAM 역할 생성 가이드

## 🔐 생성할 IAM 역할

1. **VideoConversionLambdaRole** - 비디오 변환 Lambda용
2. **StartStepFunctionLambdaRole** - Step Functions 시작 Lambda용
3. **AIAnalysisLambdaRole** - AI 분석 Lambda들용
4. **VideoProcessingStepFunctionsRole** - Step Functions용
5. **MediaConvertServiceRole** - MediaConvert용
6. **EventBridgeInvokeLambdaRole** - EventBridge용

---

## 🔧 AWS 콘솔에서 생성 방법

### 1. VideoConversionLambdaRole 생성

#### 1-1. 역할 생성
1. **AWS IAM 콘솔** → **역할** → **역할 만들기**
2. **신뢰할 수 있는 엔터티 유형**: AWS 서비스
3. **사용 사례**: Lambda
4. **다음** 클릭

#### 1-2. 권한 정책 연결
다음 AWS 관리형 정책들을 검색하여 연결:
- `AWSLambdaBasicExecutionRole`

#### 1-3. 인라인 정책 추가
**정책 이름**: `VideoConversionPolicy`

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::video-input-pipeline-*/*",
                "arn:aws:s3:::video-output-pipeline-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "mediaconvert:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": "arn:aws:iam::*:role/MediaConvertServiceRole"
        }
    ]
}
```

#### 1-4. 역할 이름 설정
- **역할 이름**: `VideoConversionLambdaRole`
- **역할 만들기** 클릭

---

### 2. StartStepFunctionLambdaRole 생성

#### 2-1. 역할 생성
1. **역할 만들기** → **AWS 서비스** → **Lambda**

#### 2-2. 권한 정책 연결
- `AWSLambdaBasicExecutionRole`

#### 2-3. 인라인 정책 추가
**정책 이름**: `StartStepFunctionPolicy`

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "states:StartExecution"
            ],
            "Resource": "arn:aws:states:ap-northeast-2:*:stateMachine:VideoProcessingWorkflow"
        }
    ]
}
```

#### 2-4. 역할 이름
- **역할 이름**: `StartStepFunctionLambdaRole`

---

### 3. AIAnalysisLambdaRole 생성

#### 3-1. 역할 생성
1. **역할 만들기** → **AWS 서비스** → **Lambda**

#### 3-2. 권한 정책 연결
- `AWSLambdaBasicExecutionRole`

#### 3-3. 인라인 정책 추가
**정책 이름**: `AIAnalysisPolicy`

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::video-output-pipeline-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "transcribe:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "rekognition:*"
            ],
            "Resource": "*"
        }
    ]
}
```

#### 3-4. 역할 이름
- **역할 이름**: `AIAnalysisLambdaRole`

---

### 4. VideoProcessingStepFunctionsRole 생성

#### 4-1. 역할 생성
1. **역할 만들기** → **AWS 서비스** → **Step Functions**

#### 4-2. 권한 정책 연결
- `AWSStepFunctionsFullAccess`

#### 4-3. 인라인 정책 추가
**정책 이름**: `InvokeLambdaPolicy`

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:ap-northeast-2:*:function:TranscribeLambda",
                "arn:aws:lambda:ap-northeast-2:*:function:TwelvlabsLamda"
            ]
        }
    ]
}
```

#### 4-4. 역할 이름
- **역할 이름**: `VideoProcessingStepFunctionsRole`

---

### 5. MediaConvertServiceRole 생성

#### 5-1. 역할 생성
1. **역할 만들기** → **AWS 서비스** → **MediaConvert**

#### 5-2. 권한 정책 연결
- `AmazonS3FullAccess`

#### 5-3. 역할 이름
- **역할 이름**: `MediaConvertServiceRole`

---

### 6. EventBridgeInvokeLambdaRole 생성

#### 6-1. 역할 생성
1. **역할 만들기** → **AWS 서비스** → **EventBridge**

#### 6-2. 인라인 정책 추가
**정책 이름**: `InvokeLambdaPolicy`

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:ap-northeast-2:*:function:video-conversion-lambda",
                "arn:aws:lambda:ap-northeast-2:*:function:StartStepFunctionLambda"
            ]
        }
    ]
}
```

#### 6-3. 역할 이름
- **역할 이름**: `EventBridgeInvokeLambdaRole`

---

## ✅ 확인 사항

- [ ] VideoConversionLambdaRole 생성 완료
- [ ] StartStepFunctionLambdaRole 생성 완료
- [ ] AIAnalysisLambdaRole 생성 완료
- [ ] VideoProcessingStepFunctionsRole 생성 완료
- [ ] MediaConvertServiceRole 생성 완료
- [ ] EventBridgeInvokeLambdaRole 생성 완료

## 📝 참고사항

- 계정 ID를 실제 AWS 계정 ID로 변경하세요
- 리소스 ARN의 리전이 ap-northeast-2인지 확인하세요
- 인라인 정책 추가 시 JSON 형식을 정확히 입력하세요
