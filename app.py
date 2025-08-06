from flask import Flask, render_template, request, jsonify, send_file
import os
import boto3
import json
import logging
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB max file size

# AWS 설정
AWS_REGION = 'ap-northeast-2'
S3_BUCKET = 'video-processing-bucket-' + str(hash(os.urandom(16)))[:8]

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# S3 클라이언트 초기화
s3_client = boto3.client('s3', region_name=AWS_REGION)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/v1/s3_upload', methods=['POST'])
def s3_upload():
    """S3에 파일 업로드를 위한 presigned URL 생성"""
    try:
        if 'video' not in request.files:
            return jsonify({"error": "No video file part"}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        filename = secure_filename(file.filename)
        
        # Presigned URL 생성
        try:
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': S3_BUCKET, 'Key': filename},
                ExpiresIn=3600  # 1시간
            )
            
            return jsonify({
                "presigned_url": presigned_url,
                "bucket": S3_BUCKET,
                "key": filename
            })
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return jsonify({"error": "Failed to generate upload URL"}), 500
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/bucket_list', methods=['GET'])
def bucket_list():
    """S3 버킷 목록 조회"""
    try:
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        return jsonify({"buckets": buckets})
    except ClientError as e:
        logger.error(f"Error listing buckets: {e}")
        return jsonify({"error": "Failed to list buckets"}), 500

@app.route('/api/v1/objects/<bucket_name>', methods=['GET'])
def list_objects(bucket_name):
    """특정 버킷의 객체 목록 조회"""
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        objects = []
        if 'Contents' in response:
            objects = [obj['Key'] for obj in response['Contents']]
        return jsonify({"objects": objects})
    except ClientError as e:
        logger.error(f"Error listing objects: {e}")
        return jsonify({"error": "Failed to list objects"}), 500

@app.route('/api/v1/download/<bucket_name>/<path:object_key>', methods=['GET'])
def download_object(bucket_name, object_key):
    """S3 객체 다운로드"""
    try:
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            s3_client.download_fileobj(bucket_name, object_key, tmp_file)
            tmp_file_path = tmp_file.name
        
        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=object_key.split('/')[-1]
        )
    except ClientError as e:
        logger.error(f"Error downloading object: {e}")
        return jsonify({"error": "Failed to download object"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({"status": "healthy", "service": "video-edit-api"})

if __name__ == '__main__':
    # S3 버킷 생성 (존재하지 않는 경우)
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET)
        logger.info(f"Bucket {S3_BUCKET} already exists")
    except ClientError:
        try:
            s3_client.create_bucket(
                Bucket=S3_BUCKET,
                CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
            )
            logger.info(f"Created bucket {S3_BUCKET}")
        except ClientError as e:
            logger.error(f"Error creating bucket: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
