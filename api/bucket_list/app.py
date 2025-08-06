from flask import Flask, jsonify, render_template
import boto3
import json
import os

app = Flask(__name__)


def load_output_json(bucket_name):
    s3 = boto3.client('s3')

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
    BUCKET_NAME = 'video-input-pipeline-20250724'
    result = load_output_json(BUCKET_NAME)
    if result is not None:
        return jsonify(result)  # 리스트 형식으로 JSON 응답
    else:
        return jsonify({"error": "S3 접근 오류"}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
