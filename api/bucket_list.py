from flask import Flask, jsonify, render_template
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
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    aws_session_token=session_token
                )
            else:
                print("세션 토큰 없이 자격 증명으로 연결합니다.")
                return boto3.client(
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key
                )
    else:
        raise Exception("AWS credentials not found.")

def load_output_json(bucket_name):
    s3 = get_s3_client()

    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        bucket_json = response.get("Contents", [])

        # 단순 리스트 형식으로 반환
        key_objects = [obj["Key"] for obj in bucket_json]
        return key_objects  # 리스트 형식으로 반환

    except Exception as e:
        print(f"S3 접근 중 오류: {e}")
        return None


# @app.route('/')
# def index():
#     return render_template('index.html')

@app.route('/api/v1/bucketdata', methods=['GET'])
def get_s3_list():
    BUCKET_NAME = 'testbucket3311c'
    result = load_output_json(BUCKET_NAME)
    if result is not None:
        return jsonify(result)  # 리스트 형식으로 JSON 응답
    else:
        return jsonify({"error": "S3 접근 오류"}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
