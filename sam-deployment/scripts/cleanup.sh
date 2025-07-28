#!/bin/bash

# AWS Video Processing Pipeline SAM 정리 스크립트

set -e

echo "🧹 AWS Video Processing Pipeline 리소스를 정리합니다..."

# 기본 설정
STACK_NAME="video-processing-pipeline"
REGION="ap-northeast-2"
DATE_SUFFIX=$(date +%Y%m%d)

# 사용자 확인
echo "⚠️  이 작업은 다음 리소스들을 삭제합니다:"
echo "  - CloudFormation Stack: $STACK_NAME"
echo "  - S3 Buckets: video-input-pipeline-$DATE_SUFFIX, video-output-pipeline-$DATE_SUFFIX"
echo "  - Lambda Functions, Step Functions, IAM Roles 등 모든 관련 리소스"
echo ""
read -p "정말로 삭제하시겠습니까? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ 삭제가 취소되었습니다."
    exit 0
fi

# S3 버킷 내용 삭제
echo ""
echo "🗑️  S3 버킷 내용을 삭제합니다..."

INPUT_BUCKET="video-input-pipeline-$DATE_SUFFIX"
OUTPUT_BUCKET="video-output-pipeline-$DATE_SUFFIX"

# 입력 버킷 비우기
if aws s3 ls "s3://$INPUT_BUCKET" --region $REGION > /dev/null 2>&1; then
    echo "  - $INPUT_BUCKET 버킷을 비웁니다..."
    aws s3 rm "s3://$INPUT_BUCKET" --recursive --region $REGION
else
    echo "  - $INPUT_BUCKET 버킷이 존재하지 않습니다."
fi

# 출력 버킷 비우기
if aws s3 ls "s3://$OUTPUT_BUCKET" --region $REGION > /dev/null 2>&1; then
    echo "  - $OUTPUT_BUCKET 버킷을 비웁니다..."
    aws s3 rm "s3://$OUTPUT_BUCKET" --recursive --region $REGION
else
    echo "  - $OUTPUT_BUCKET 버킷이 존재하지 않습니다."
fi

# CloudFormation 스택 삭제
echo ""
echo "🗑️  CloudFormation 스택을 삭제합니다..."
if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION > /dev/null 2>&1; then
    aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION
    
    echo "⏳ 스택 삭제를 기다립니다... (몇 분 소요될 수 있습니다)"
    aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION
    
    echo "✅ CloudFormation 스택이 성공적으로 삭제되었습니다."
else
    echo "⚠️  CloudFormation 스택 '$STACK_NAME'이 존재하지 않습니다."
fi

# 남은 리소스 확인
echo ""
echo "🔍 남은 리소스를 확인합니다..."

# MediaConvert 작업 확인
echo "  - MediaConvert 작업 확인 중..."
ACTIVE_JOBS=$(aws mediaconvert list-jobs --region $REGION --query 'Jobs[?Status==`SUBMITTED` || Status==`PROGRESSING`].Id' --output text)
if [ -n "$ACTIVE_JOBS" ]; then
    echo "⚠️  활성 MediaConvert 작업이 있습니다: $ACTIVE_JOBS"
    echo "    이 작업들은 자동으로 완료되거나 수동으로 취소해야 합니다."
fi

# Transcribe 작업 확인
echo "  - Transcribe 작업 확인 중..."
ACTIVE_TRANSCRIBE=$(aws transcribe list-transcription-jobs --region $REGION --status IN_PROGRESS --query 'TranscriptionJobSummaries[].TranscriptionJobName' --output text)
if [ -n "$ACTIVE_TRANSCRIBE" ]; then
    echo "⚠️  활성 Transcribe 작업이 있습니다: $ACTIVE_TRANSCRIBE"
    echo "    이 작업들은 자동으로 완료되거나 수동으로 취소해야 합니다."
fi

echo ""
echo "🎉 리소스 정리가 완료되었습니다!"
echo ""
echo "💡 참고사항:"
echo "  - CloudWatch Logs는 자동으로 삭제되지 않습니다."
echo "  - 필요시 CloudWatch 콘솔에서 수동으로 삭제하세요."
echo "  - 진행 중인 MediaConvert/Transcribe 작업은 완료될 때까지 요금이 발생할 수 있습니다."
