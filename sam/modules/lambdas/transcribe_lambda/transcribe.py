import boto3
import time
import os

transcribe = boto3.client("transcribe")

# Output 전용 버킷
OUTPUT_BUCKET = "video-output-pipeline-20250724"

def lambda_handler(event, context):
    try:
        print("🎯 이벤트:", event)

        # EventBridge S3 ObjectCreated 이벤트에서 버킷과 키 추출
        bucket = event["detail"]["bucket"]["name"]
        key = event["detail"]["object"]["key"]
        print(f'영상 이름: {key} 버킷 이름: {bucket}')

        # Transcribe Job 이름 생성
        job_id = f"job-{int(time.time())}"
        job_name = f"transcribe-{job_id}"

        # S3 URI (input 버킷)
        s3_uri = f"s3://{bucket}/{key}"

        # output JSON 파일 경로 (output 버킷의 transcribe 폴더)
        base_name = os.path.splitext(os.path.basename(key))[0]
        output_key = f"transcribe/{base_name}.json"

        # 확장자 확인 (mp4, wav, mov 등 Transcribe 지원 형식)
        extension = key.split(".")[-1].lower()
        if extension not in ["mp3", "mp4", "wav", "flac", "ogg", "m4a", "mov"]:
            raise ValueError(f"지원하지 않는 파일 형식: {extension}")

        # Transcribe 시작
        response = transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": s3_uri},
            MediaFormat=extension,
            LanguageCode="en-US",
            OutputBucketName=OUTPUT_BUCKET,  # output 버킷으로 지정
            OutputKey=output_key
        )

        print("🚀 Transcribe 시작:", job_name)
        print("📥 입력:", s3_uri)
        print("📤 출력:", f"s3://{OUTPUT_BUCKET}/{output_key}")

        return {
            "statusCode": 200,
            "jobName": job_name,
            "inputVideo": s3_uri,
            "outputJson": f"s3://{OUTPUT_BUCKET}/{output_key}"
        }

    except Exception as e:
        print(f"❌ Transcribe 작업 실패: {str(e)}")
        return {
            "statusCode": 500,
            "error": str(e)
        }
