#!/bin/bash

# AWS Video Processing Pipeline SAM 배포 스크립트

set -e

echo "🚀 AWS Video Processing Pipeline SAM 배포를 시작합니다..."

# 기본 설정
STACK_NAME="video-processing-pipeline"
REGION="ap-northeast-2"
DATE_SUFFIX=$(date +%Y%m%d)

# 파라미터 확인
echo "📋 배포 설정:"
echo "  - Stack Name: $STACK_NAME"
echo "  - Region: $REGION"
echo "  - Date Suffix: $DATE_SUFFIX"

# 현재 디렉토리 확인 및 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "  - Project Directory: $PROJECT_DIR"
cd "$PROJECT_DIR"

# AWS CLI 설치 확인
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI가 설치되지 않았습니다. 먼저 AWS CLI를 설치해주세요."
    exit 1
fi

# SAM CLI 설치 확인
if ! command -v sam &> /dev/null; then
    echo "❌ SAM CLI가 설치되지 않았습니다. 먼저 SAM CLI를 설치해주세요."
    echo "설치 가이드: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
    exit 1
fi

# AWS 자격 증명 확인
echo "🔐 AWS 자격 증명을 확인합니다..."
if ! aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    echo "❌ AWS 자격 증명이 설정되지 않았습니다. 'aws configure'를 실행해주세요."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION)
echo "✅ AWS 계정 ID: $ACCOUNT_ID"

# Twelvlabs API 키 입력 (선택사항)
echo ""
echo "🔑 Twelvlabs API 키를 입력하세요 (선택사항, 엔터를 누르면 건너뜀):"
read -s TWELVLABS_API_KEY
if [ -z "$TWELVLABS_API_KEY" ]; then
    TWELVLABS_API_KEY="your-twelvlabs-api-key"
    echo "⚠️  Twelvlabs API 키가 설정되지 않았습니다. 나중에 Lambda 환경변수에서 설정할 수 있습니다."
fi

# SAM 빌드
echo ""
echo "🔨 SAM 애플리케이션을 빌드합니다..."
sam build

# SAM 배포
echo ""
echo "🚀 SAM 애플리케이션을 배포합니다..."
sam deploy \
    --stack-name $STACK_NAME \
    --region $REGION \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        DateSuffix=$DATE_SUFFIX \
        TwelvlabsApiKey=$TWELVLABS_API_KEY \
    --confirm-changeset

# 배포 결과 확인
echo ""
echo "📊 배포된 리소스를 확인합니다..."

# 스택 출력 가져오기
OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs' \
    --output table)

echo "✅ 배포 완료!"
echo ""
echo "📋 생성된 리소스:"
echo "$OUTPUTS"

# 테스트 가이드
echo ""
echo "🧪 테스트 방법:"
echo "1. 입력 버킷에 비디오 파일을 업로드하세요:"
echo "   aws s3 cp your-video.mp4 s3://video-input-pipeline-$DATE_SUFFIX/"
echo ""
echo "2. CloudWatch Logs에서 처리 과정을 모니터링하세요:"
echo "   - /aws/lambda/video-conversion-lambda"
echo "   - /aws/lambda/StartStepFunctionLambda"
echo "   - /aws/lambda/TranscribeLambda"
echo "   - /aws/lambda/TwelvlabsLambda"
echo ""
echo "3. Step Functions 콘솔에서 워크플로우 실행을 확인하세요:"
echo "   https://console.aws.amazon.com/states/home?region=$REGION"
echo ""
echo "4. 출력 버킷에서 결과를 확인하세요:"
echo "   aws s3 ls s3://video-output-pipeline-$DATE_SUFFIX/ --recursive"

echo ""
echo "🎉 배포가 성공적으로 완료되었습니다!"
