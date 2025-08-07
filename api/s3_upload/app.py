from flask import Flask, jsonify, request
import json
import boto3
import logging
from botocore.exceptions import ClientError
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/v1/s3_input', methods=['POST'])
def s3_upload():

    s3 = boto3.client('s3')

    bucket = "video-input-pipeline-20250724"
    data = request.get_json()
    filename = data.get('filename')  
    content_type = data.get('contentType')

    if not content_type:
        return jsonify({"error": "contentType is required"}), 400

    try:
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params= {"Bucket": bucket, "Key": filename, "ContentType": content_type},
            ExpiresIn=1000
        )
    except ClientError as e:
        logging.error(f"Couldn't generate presigned URL: {e}")
        return jsonify({"error": "Could not generate URL"}), 500
    
    return jsonify({"uploadUrl": url})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)