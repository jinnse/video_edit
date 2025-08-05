from flask import Flask, jsonify, request
import json
import boto3
import logging
from botocore.exceptions import ClientError

@app.route('/api/v1/s3_intput', methods=['GET'])
def s3_upload():
    if 'video' not in request.files:
        return jsonify({"error": "No video file part"}), 400
    
    file_name = request.files['video']

    s3 = boto3.client('s3')

    bucket = ""
    filename = request.arg.get('filename')

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