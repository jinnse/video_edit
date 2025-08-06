from flask import Flask, jsonify, request
import boto3
import json
import os
from dotenv import load_dotenv
import logging
import uuid

from botocore.exceptions import ClientError


app = Flask(__name__)
logger = logging.getLogger(__name__)

def invoke_agent(client, agent_id, alias_id, prompt, session_id):
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            enableTrace=True,
            sessionId = session_id,
            inputText=prompt,
            streamingConfigurations = { 
    "applyGuardrailInterval" : 20,
      "streamFinalResponse" : False
            }
        )
        completion = ""
        for event in response.get("completion"):
            #Collect agent output.
            if 'chunk' in event:
                chunk = event["chunk"]
                completion += chunk["bytes"].decode()
            
            # Log trace output.
            if 'trace' in event:
                trace_event = event.get("trace")
                trace = trace_event['trace']
                for key, value in trace.items():
                    logging.info("%s: %s",key,value)

        print(f"Agent response: {completion}")

@app.route('/api/v1/lambda_function', methods=['GET'])
def lambda_client():
    selected_video = request.args.get('selectedVideo')
    selected_count = request.args.get('selectedCount')
    selected_type = request.args.get('selectedType')
    prompt = request.args.get('prompt')

    ai_prompt = {
        "selectedVideo": selected_video,
        "selectedCount": selected_count,
        "selectedType": selected_type,
        "prompt": prompt
    }

    client=boto3.client(
            service_name="bedrock-agent-runtime",
            region_name="ap-northeast-2") 
    
    agent_id = "trans"
    alias_id = "DRAFT"
    session_id = str(uuid.uuid4()) # 겹치지 않게 일회성 생성
    prompt = ai_prompt

    try:
        response_payload = invoke_agent(client, agent_id, alias_id, prompt, session_id)

        return jsonify(response_payload)

    except ClientError as e:
        print(f"Client error: {str(e)}")
        logger.error("Client error: %s", {str(e)})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
