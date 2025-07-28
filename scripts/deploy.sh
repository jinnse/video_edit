#!/bin/bash

# 비디오 처리 파이프라인 배포 스크립트
set -e

REGION="ap-northeast-2"
CONFIG_FILE="config/prod.json"

echo "🚀 비디오 처리 파이프라인 배포 시작..."

# 함수 배포 함수
deploy_lambda() {
    local function_dir=$1
    local function_name=$2
    
    echo "📦 $function_name 패키징 중..."
    cd "lambda-functions/$function_dir"
    zip -r "../../$function_name.zip" . -x "*.git*" "*.DS_Store*"
    cd ../..
    
    echo "🚀 $function_name 배포 중..."
    aws lambda update-function-code \
        --function-name "$function_name" \
        --zip-file "fileb://$function_name.zip" \
        --region "$REGION"
    
    echo "✅ $function_name 배포 완료"
    rm "$function_name.zip"
}

# 변경된 함수만 배포
if [ "$1" = "all" ] || [ "$1" = "twelvelabs" ]; then
    deploy_lambda "twelvelabs-lambda" "TwelvlabsLamda"
fi

if [ "$1" = "all" ] || [ "$1" = "video-conversion" ]; then
    deploy_lambda "video-conversion-lambda" "video-conversion-lambda"
fi

if [ "$1" = "all" ] || [ "$1" = "start-stepfunction" ]; then
    deploy_lambda "start-stepfunction-lambda" "StartStepFunctionLambda"
fi

if [ "$1" = "all" ] || [ "$1" = "transcribe" ]; then
    deploy_lambda "transcribe-lambda" "TranscribeLambda"
fi

if [ "$1" = "all" ] || [ "$1" = "rekognition" ]; then
    deploy_lambda "rekognition-lambda" "RekognitionLambda"
fi

# Step Functions 업데이트
if [ "$1" = "all" ] || [ "$1" = "stepfunctions" ]; then
    echo "🔄 Step Functions 업데이트 중..."
    aws stepfunctions update-state-machine \
        --state-machine-arn "arn:aws:states:ap-northeast-2:567279714866:stateMachine:VideoProcessingWorkflow" \
        --definition file://step-functions/video-processing-workflow.json \
        --region "$REGION"
    echo "✅ Step Functions 업데이트 완료"
fi

echo "🎉 배포 완료!"

# 사용법 출력
if [ -z "$1" ]; then
    echo ""
    echo "사용법:"
    echo "  ./scripts/deploy.sh all                 # 모든 리소스 배포"
    echo "  ./scripts/deploy.sh twelvelabs          # TwelveLabs Lambda만 배포"
    echo "  ./scripts/deploy.sh video-conversion    # 비디오 변환 Lambda만 배포"
    echo "  ./scripts/deploy.sh start-stepfunction  # Step Function 시작 Lambda만 배포"
    echo "  ./scripts/deploy.sh transcribe          # Transcribe Lambda만 배포"
    echo "  ./scripts/deploy.sh stepfunctions       # Step Functions만 업데이트"
fi
