from flask import Flask, jsonify, request
import json
import boto3
import logging
from botocore.exceptions import ClientError
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/v1/s3_intput', methods=['POST'])
def s3_upload():

    s3 = boto3.client('s3')

    bucket = "video-input-pipeline-20250724"
    filename = request.json.get('filename')

    try:
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params= {"Bucket": bucket, "Key": filename},
            ExpiresIn=1000
        )
    except ClientError:
        print(f"Couldn't get a presigned URL for client method '{url}'.")
        raise
    
    return url

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)