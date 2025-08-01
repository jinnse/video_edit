import json
import boto3
import time

transcribe = boto3.client('transcribe')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    try:
        print(f"📝 Transcribe Lambda 시작: {json.dumps(event)}")

        # 필수 입력값
        job_id = event.get('jobId')
        output_bucket = event.get('outputBucket')
        prefix = event.get('prefix', 'converted/')
        media_format = event.get('mediaFormat', 'mp4')
        title = event.get('title')  # 확장자 제거된 파일 이름
        language_code = event.get('languageCode', 'ko-KR')  # ✅ 언어 코드 추가 (기본값: 한국어)

        if not job_id or not output_bucket or not title:
            raise ValueError("jobId, outputBucket, title은 필수입니다.")

        print(f"🌐 사용할 언어 코드: {language_code}")

        # 변환된 영상 찾기
        converted_video_key = find_converted_video(output_bucket, prefix, media_format)
        if not converted_video_key:
            raise ValueError(f"변환된 비디오 파일을 찾을 수 없습니다. jobId: {job_id}")

        video_uri = f"s3://{output_bucket}/{converted_video_key}"
        transcribe_job_name = f"transcribe-{job_id}-{int(time.time())}"

        output_key = f"transcribe/{title}.json"

        # Transcribe 비동기 작업 시작
        transcribe.start_transcription_job(
            TranscriptionJobName=transcribe_job_name,
            Media={'MediaFileUri': video_uri},
            MediaFormat=media_format,
            LanguageCode=language_code,  # ✅ 언어 코드 추가
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 10
            },
            OutputBucketName=output_bucket,
            OutputKey=output_key
        )

        print(f"✅ Transcribe 작업 시작됨: {transcribe_job_name} (언어: {language_code})")

        return {
            'statusCode': 200,
            'transcribeJobName': transcribe_job_name,
            'transcribeStatus': 'IN_PROGRESS',
            'jobId': job_id,
            'videoUri': video_uri,
            'outputBucket': output_bucket,
            'outputKey': converted_video_key,
            'languageCode': language_code
        }

    except Exception as e:
        print(f"❌ Transcribe 작업 실패: {str(e)}")
        return {
            'statusCode': 500,
            'transcribeStatus': 'FAILED',
            'error': str(e),
            'jobId': event.get('jobId', 'unknown')
        }

def find_converted_video(bucket, prefix, media_format):
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)
        if 'Contents' not in response:
            return None

        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith(f'.{media_format}') and '.write_access_check_file.temp' not in key:
                print(f"🔍 찾은 변환 파일: {key}")
                return key

        latest_file = max(response['Contents'], key=lambda x: x['LastModified'], default=None)
        if latest_file and latest_file['Key'].endswith(f'.{media_format}'):
            print(f"🔍 최신 파일 사용: {latest_file['Key']}")
            return latest_file['Key']

        return None

    except Exception as e:
        print(f"❌ S3 탐색 실패: {str(e)}")
        return None
