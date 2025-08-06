from flask import Flask, render_template, jsonify
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({"status": "healthy", "service": "video-edit-api"})

@app.route('/api/v1/bucket_list', methods=['GET'])
def bucket_list():
    """S3 버킷 목록 조회 (테스트용)"""
    return jsonify({"buckets": ["test-bucket-1", "test-bucket-2"]})

@app.route('/api/v1/objects/<bucket_name>', methods=['GET'])
def list_objects(bucket_name):
    """특정 버킷의 객체 목록 조회 (테스트용)"""
    return jsonify({"objects": ["test-file-1.mp4", "test-file-2.mp4"]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
