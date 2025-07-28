# Lambda Functions

현재 AWS 환경에 배포된 Lambda 함수들

## 함수 목록

1. **twelvelabs-lambda** - TwelveLabs API 연동
2. **video-conversion-lambda** - MediaConvert를 이용한 비디오 변환
3. **start-stepfunction-lambda** - Step Functions 워크플로우 시작
4. **transcribe-lambda** - Amazon Transcribe 음성 인식
5. **rekognition-lambda** - Amazon Rekognition 이미지 분석 (현재 미사용)

## 배포 방법

각 함수 디렉토리에서:
```bash
zip -r function.zip .
aws lambda update-function-code --function-name FUNCTION_NAME --zip-file fileb://function.zip
```
