from flask import Flask, jsonify, request
import json
import boto3
import logging
from botocore.exceptions import ClientError

app = Flask(__name__)

@app.route('/api/v1/s3_intput', methods=['POST'])
def s3_upload():
    
    file_name = request.get('file_name')

    s3 = boto3.client('s3')

    bucket = ""
    filename = request.post('filename')

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