from flask import Flask, jsonify, request
import boto3
import json
import os
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv(dotenv_path='aws_credentials.env')

def get_s3_client():
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    session_token = os.getenv('AWS_SESSION_TOKEN')

    if access_key and secret_key:
            if session_token:
                print("세션 토큰을 포함한 자격 증명으로 연결합니다.")
                return boto3.client(
                    'lambda',
                    region_name='ap-northeast-2',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    aws_session_token=session_token
                )
            else:
                print("세션 토큰 없이 자격 증명으로 연결합니다.")
                return boto3.client(
                    'lambda',
                    region_name='ap-northeast-2',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key
                )
    else:
        raise Exception("AWS credentials not found.")

@app.route('/api/v1/lambda_function', methods=['GET'])
def lambda_client():
    selected_video = request.args.get('selectedVideo')
    selected_count = request.args.get('selectedCount')
    selected_type = request.args.get('selectedType')
    prompt = request.args.get('prompt')

    payload = {
        "selectedVideo": selected_video,
        "selectedCount": selected_count,
        "selectedType": selected_type,
        "prompt": prompt
    }

    try:
        response = lambda_client.invoke(
            FunctionName='TEST_LAMBDA',
            InvocationType='RequestResponse',  # 비동기이면 'Event'
            Payload=json.dumps(payload)
        )

        response_payload = json.load(response['Payload'])
        return jsonify(response_payload)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)