import json
import boto3
import uuid
import urllib.parse

# AWS 클라이언트
sf_client = boto3.client('stepfunctions')
ec2_client = boto3.client('ec2')

# Step Function ARN
STATE_MACHINE_ARN = 'arn:aws:states:ap-northeast-2:567279714866:stateMachine:VideoProcessingWorkflow'

# 기본 설정값
DEFAULT_INPUT_BUCKET = "video-input-pipeline-20250724"
DEFAULT_NAME_MODIFIER = "_converted"
DEFAULT_PREFIX = "converted/"
DEFAULT_MEDIA_FORMAT = "mp4"
DEFAULT_LANGUAGE_CODE = "ko-KR"

def get_default_subnets():
    """기본 서브넷들을 동적으로 조회"""
    try:
        response = ec2_client.describe_subnets(
            Filters=[
                {
                    'Name': 'default-for-az',
                    'Values': ['true']
                },
                {
                    'Name': 'state',
                    'Values': ['available']
                }
            ]
        )
        
        subnet_ids = [subnet['SubnetId'] for subnet in response['Subnets']]
        print(f"🔍 조회된 기본 서브넷들: {subnet_ids}")
        return subnet_ids
        
    except Exception as e:
        print(f"❌ 서브넷 조회 실패: {str(e)}")
        # 폴백으로 기존 서브넷 사용
        return ["subnet-02bb8954929605be5", "subnet-065cc5f0479687b56"]

def lambda_handler(event, context):
    print("📥 EventBridge에서 받은 S3 이벤트:")
    print(json.dumps(event, indent=2, ensure_ascii=False))

    try:
        # 1. 동적으로 기본 서브넷 조회
        subnets = get_default_subnets()
        
        # 2. S3 이벤트에서 버킷과 key 추출
        output_bucket = event['detail']['bucket']['name']
        key = urllib.parse.unquote(event['detail']['object']['key'])
        filename = key.split("/")[-1]

        # 3. 원본 파일명 추정
        if '.' in filename:
            name_part, ext = filename.rsplit('.', 1)
            if name_part.endswith(DEFAULT_NAME_MODIFIER):
                original_filename = name_part.removesuffix(DEFAULT_NAME_MODIFIER) + '.' + ext
            else:
                original_filename = filename
        else:
            original_filename = filename
            ext = ''

        # 4. S3 경로 구성
        s3_path = f"s3://{output_bucket}/{key}"
        bucket_path = f"s3://{output_bucket}/"
        output_destination = f"s3://{output_bucket}/{DEFAULT_PREFIX}"

        # 5. Step Function input 구성
        step_input = {
            "detail": {
                "jobId": str(uuid.uuid4()),
                "status": "CREATED",
                "title": original_filename.rsplit('.', 1)[0],
                "originalFilename": original_filename,
                "s3Path": s3_path,
                "bucket_path": bucket_path,
                "inputBucket": DEFAULT_INPUT_BUCKET,
                "outputBucket": output_bucket,
                "outputDestination": output_destination,
                "nameModifier": DEFAULT_NAME_MODIFIER,
                "prefix": DEFAULT_PREFIX,
                "mediaFormat": ext if ext else DEFAULT_MEDIA_FORMAT,
                "languageCode": DEFAULT_LANGUAGE_CODE,
                "subnets": subnets  # ✅ 동적으로 조회된 서브넷 사용
            }
        }

        # 로그 출력
        print("📦 Step Function에 전달할 입력 값:")
        print(json.dumps(step_input, indent=2, ensure_ascii=False))

        # Step Function 실행
        response = sf_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps(step_input)
        )

        print(f"✅ Step Function 시작됨: {response['executionArn']}")
        return {
            "statusCode": 200,
            "body": json.dumps("Step Function 실행 성공")
        }

    except Exception as e:
        print(f"❌ 실행 실패: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(f"에러 발생: {str(e)}")
        }
