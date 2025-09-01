from flask import Flask, jsonify, request, make_response
import boto3, logging
from botocore.exceptions import ClientError
from botocore.config import Config

app = Flask(__name__)

ALLOWED_ORIGINS = {"http://13.125.181.147:5003"}  # 필요시 여러 개 추가

def add_cors_headers(resp):
    origin = request.headers.get("Origin")
    # 요청 Origin이 허용 목록에 있으면 그대로 에코, 아니면 지정값/와일드카드
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
    else:
        resp.headers["Access-Control-Allow-Origin"] = "*"

    # 브라우저가 예고한 헤더/메서드 그대로 돌려줌
    req_headers = request.headers.get("Access-Control-Request-Headers", "Content-Type")
    resp.headers["Access-Control-Allow-Headers"] = req_headers
    req_method = request.headers.get("Access-Control-Request-Method", "POST")
    resp.headers["Access-Control-Allow-Methods"] = f"{req_method}, OPTIONS"

    # 캐싱 시간 (선택)
    resp.headers["Access-Control-Max-Age"] = "600"
    # Credential을 쓸 경우엔 아래를 True로 하고, Origin은 * 대신 구체값이어야 함
    # resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        resp = make_response("", 204)  # 바디 없는 204가 가장 안전
        return add_cors_headers(resp)

@app.after_request
def apply_cors(resp):
    # 모든 정상/에러 응답에 CORS 헤더 부착
    return add_cors_headers(resp)

@app.route('/api/v1/s3_input', methods=['POST'])
def s3_upload():
    # 여기까지 왔다는 건 프리플라이트가 2xx로 통과했다는 뜻
    s3 = boto3.client(
        's3',
        region_name='ap-northeast-2',
        config=Config(signature_version='s3v4')
    )
    bucket = "video-input-pipeline-20250724"
    data = request.get_json(silent=True) or {}
    filename = data.get('filename')
    content_type = data.get('contentType')

    if not filename or not content_type:
        return jsonify({"error": "filename and contentType are required"}), 400

    try:
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": bucket, "Key": filename, "ContentType": content_type},
            ExpiresIn=1000
        )
        return jsonify({"uploadUrl": url}), 200
    except ClientError as e:
        logging.exception("Couldn't generate presigned URL")
        return jsonify({"error": "Could not generate URL"}), 500

if __name__ == "__main__":
    # prod에서는 반드시 WSGI 서버(gunicorn/uwsgi) + 프록시에서 OPTIONS 전달 설정
    app.run(debug=True, host='0.0.0.0', port=5000)
