import os
import json
import logging
from typing import Any, Dict
from flask import Flask, jsonify, request
from flask_cors import CORS
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("video-ai-backend")

AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")

# Flow 설정
FLOW_IDENTIFIER = os.getenv("FLOW_IDENTIFIER", "8FT99SKAF6")
FLOW_ALIAS_IDENTIFIER = os.getenv("FLOW_ALIAS_IDENTIFIER", "P37AGF904J")
FLOW_INPUT_NODE_NAME = os.getenv("FLOW_INPUT_NODE_NAME", "FlowInputNode")

ALLOWED_ORIGINS = ["https://www.videofinding.com"]

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS, "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

def get_runtime():
    return boto3.client("bedrock-agent-runtime", region_name=AWS_REGION, config=Config(read_timeout=600, connect_timeout=60, retries={"max_attempts": 5}))

def get_buildtime():
    # Flows의 조회(존재/별칭 매핑 확인)는 build-time API(서비스명: bedrock-agent)를 사용
    return boto3.client("bedrock-agent", region_name=AWS_REGION, config=Config(read_timeout=300, connect_timeout=30, retries={"max_attempts": 5}))

def to_jsonable(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return json.loads(json.dumps(obj, default=str))

def parse_request(req) -> Dict[str, Any]:
    if req.method == "POST":
        data = req.get_json(silent=True) or {}
        return {
            "selectedVideo": data.get("selectedVideo"),
            "selectedCount": data.get("selectedCount"),
            "selectedType": data.get("selectedType"),
            "prompt": data.get("prompt")
        }
    return {
        "selectedVideo": req.args.get("selectedVideo"),
        "selectedCount": req.args.get("selectedCount"),
        "selectedType": req.args.get("selectedType"),
        "prompt": req.args.get("prompt")
    }

def invoke_flow(flow_identifier: str, flow_alias_identifier: str, flow_input_node_name: str, ai_prompt: Dict[str, Any]) -> Dict[str, Any]:
    client = get_runtime()
    logger.info("[InvokeFlow] flow=%s alias=%s node=%s", flow_identifier, flow_alias_identifier, flow_input_node_name)

    # Flow Input Node가 STRING을 기대하므로 JSON 문자열로 변환
    ai_prompt_string = json.dumps(ai_prompt, ensure_ascii=False)
    logger.info("[InvokeFlow] input data: %s", ai_prompt_string)

    resp = client.invoke_flow(
        flowIdentifier=flow_identifier,
        flowAliasIdentifier=flow_alias_identifier,
        enableTrace=True,
        inputs=[{
            "content": {"document": ai_prompt_string},  # OBJECT → STRING으로 변경
            "nodeName": flow_input_node_name,
            "nodeOutputName": "document"
        }]
        # modelPerformanceConfiguration 제거 - ap-northeast-2에서 지원하지 않음
    )

    result = {"ok": True, "executionId": resp.get("executionId"), "outputs": [], "completionReason": None, "trace": []}
    stream = resp.get("responseStream")
    if stream is None:
        raise RuntimeError("responseStream 없음 — Flow 호출 실패")

    for event in stream:
        if "flowOutputEvent" in event:
            doc = event["flowOutputEvent"]["content"].get("document")
            result["outputs"].append(to_jsonable(doc))
        elif "flowCompletionEvent" in event:
            result["completionReason"] = event["flowCompletionEvent"].get("completionReason")
        elif "flowMultiTurnInputRequestEvent" in event:
            req_doc = event["flowMultiTurnInputRequestEvent"]["content"].get("document")
            return {"ok": False, "error": "INPUT_REQUIRED", "requestedInput": to_jsonable(req_doc), "executionId": result["executionId"]}
        elif "flowTraceEvent" in event:
            result["trace"].append(to_jsonable(event["flowTraceEvent"]["trace"]))
        elif "validationException" in event:
            raise RuntimeError(f"ValidationException: {event['validationException'].get('message')}")
        elif "resourceNotFoundException" in event:
            raise RuntimeError(f"ResourceNotFound: {event['resourceNotFoundException']}")
        elif "throttlingException" in event:
            raise RuntimeError(f"Throttling: {event['throttlingException']}")
        elif "accessDeniedException" in event:
            raise RuntimeError(f"AccessDenied: {event['accessDeniedException']}")
        elif "badGatewayException" in event:
            raise RuntimeError(f"BadGateway: {event['badGatewayException']}")
        elif "internalServerException" in event:
            raise RuntimeError(f"InternalServer: {event['internalServerException']}")

    if not result["outputs"]:
        raise RuntimeError("FlowOutput 비어 있음 — Output 노드 연결/표현식/노드 이름 점검")

    # Flow 출력에서 S3 URL 추출
    last_output = result["outputs"][-1]
    video_url = None
    video_filename = None
    cloudfront_url = None
    thumbnail_url = None
    
    # JSON 객체인 경우 처리
    if isinstance(last_output, dict):
        logger.info(f"Processing JSON output: {last_output}")
        
        # cut_video 객체에서 정보 추출
        if "cut_video" in last_output:
            cut_video = last_output["cut_video"]
            video_url = cut_video.get("video_url")
            video_filename = cut_video.get("filename")
            
            if video_filename:
                # CloudFront URL 생성
                cloudfront_url = f"https://d1nmrhn4eusal2.cloudfront.net/{video_filename}"
                
                # 썸네일 파일명 생성 (.mp4 → .jpg)
                thumbnail_filename = video_filename.replace('.mp4', '.jpg')
                thumbnail_url = f"https://d3il8axvt9p9ix.cloudfront.net/{thumbnail_filename}"
                
                logger.info(f"Extracted from JSON - filename: {video_filename}")
                logger.info(f"Generated CloudFront URL: {cloudfront_url}")
                logger.info(f"Generated thumbnail URL: {thumbnail_url}")
    
    # 문자열인 경우 기존 로직 사용
    elif isinstance(last_output, str):
        logger.info(f"Processing string output: {last_output}")
        
        # URL 패턴 찾기 - S3 URL과 프리사인 URL 모두 지원
        import re
        # S3 URL 패턴 (쿼리 파라미터 없음)
        s3_url_pattern = r'https://[^\s\)]+\.s3\.amazonaws\.com/[^\s\)]+\.mp4'
        # 프리사인 URL 패턴 (쿼리 파라미터 있음) - 더 정확한 패턴
        presigned_url_pattern = r'https://[^\s\)]+\.mp4\?[^\)\s]+'
        # 마크다운 링크 패턴 [텍스트](URL)
        markdown_link_pattern = r'\[[^\]]+\]\(([^)]+)\)'
        
        # 여러 비디오 URL 추출
        video_urls = []
        video_filenames = []
        cloudfront_urls = []
        thumbnail_urls = []
        
        # 마크다운 링크에서 URL 추출
        markdown_links = re.findall(markdown_link_pattern, last_output)
        logger.info(f"Found markdown links: {markdown_links}")
        
        # 마크다운 링크에서 프리사인 URL 찾기
        for link in markdown_links:
            if '.mp4?' in link and 's3.amazonaws.com' in link:
                video_urls.append(link)
                logger.info(f"Found presigned URL from markdown: {link}")
        
        # S3 URL 찾기
        s3_urls = re.findall(s3_url_pattern, last_output)
        presigned_urls = re.findall(presigned_url_pattern, last_output)
        
        logger.info(f"Found S3 URLs: {s3_urls}")
        logger.info(f"Found presigned URLs: {presigned_urls}")
        
        # 중복 제거하면서 모든 URL 수집
        all_urls = list(set(video_urls + s3_urls + presigned_urls))
        logger.info(f"Total unique URLs found: {len(all_urls)}")
        
        # 각 URL에서 파일명 추출하고 CloudFront URL 생성
        for video_url in all_urls:
            # URL에서 파일명 추출 (확장자 포함)
            url_parts = video_url.split('/')
            video_filename = None
            for part in reversed(url_parts):
                if part.endswith('.mp4'):
                    video_filename = part
                    break
            
            if not video_filename:
                # 기존 정규식 방법 시도
                filename_pattern = r'/([^/]+\.mp4)(?:\?|$)'
                filename_match = re.search(filename_pattern, video_url)
                if filename_match:
                    video_filename = filename_match.group(1)
            
            if video_filename:
                # CloudFront URL 생성
                cloudfront_url = f"https://d1nmrhn4eusal2.cloudfront.net/{video_filename}"
                
                # 썸네일 파일명 생성 (.mp4 → .jpg)
                thumbnail_filename = video_filename.replace('.mp4', '.jpg')
                thumbnail_url = f"https://d3il8axvt9p9ix.cloudfront.net/{thumbnail_filename}"
                
                video_filenames.append(video_filename)
                cloudfront_urls.append(cloudfront_url)
                thumbnail_urls.append(thumbnail_url)
                
                logger.info(f"Generated CloudFront URL: {cloudfront_url}")
                logger.info(f"Generated thumbnail URL: {thumbnail_url}")
            else:
                logger.warning(f"Could not extract filename from URL: {video_url}")
        
        # URL이 없는 경우 텍스트에서 파일명 추출 시도
        if len(all_urls) == 0:
            logger.info("No URLs found, attempting to extract filenames from text")
            
            # 파일명 패턴 찾기 (예: soccer_0s-34s.mp4, soccer_40s-72s.mp4 등)
            # 여러 패턴을 시도
            filename_patterns = [
                r'(\w+_\d+s-\d+s_short\.mp4)',  # soccer_15s-410s_short.mp4
                r'(\w+_\d+s-\d+s\.mp4)',  # soccer_0s-34s.mp4
                r'(\w+_\d+-\d+\.mp4)',    # soccer_0-34.mp4
                r'(\w+_\d+s-\d+\.mp4)',   # soccer_0s-34.mp4
                r'(\w+_\d+-\d+s\.mp4)',   # soccer_0-34s.mp4
            ]
            
            found_filenames = []
            for pattern in filename_patterns:
                matches = re.findall(pattern, last_output)
                found_filenames.extend(matches)
                if matches:
                    logger.info(f"Found filenames with pattern {pattern}: {matches}")
            
            # 중복 제거
            found_filenames = list(set(found_filenames))
            logger.info(f"Total unique filenames found: {found_filenames}")
            
            for filename in found_filenames:
                # CloudFront URL 생성
                cloudfront_url = f"https://d1nmrhn4eusal2.cloudfront.net/{filename}"
                
                # 썸네일 파일명 생성 (.mp4 → .jpg)
                thumbnail_filename = filename.replace('.mp4', '.jpg')
                thumbnail_url = f"https://d3il8axvt9p9ix.cloudfront.net/{thumbnail_filename}"
                
                video_filenames.append(filename)
                cloudfront_urls.append(cloudfront_url)
                thumbnail_urls.append(thumbnail_url)
                
                logger.info(f"Generated CloudFront URL from filename: {cloudfront_url}")
                logger.info(f"Generated thumbnail URL from filename: {thumbnail_url}")
        
        # 첫 번째 비디오 정보 (하위 호환성)
        video_url = all_urls[0] if all_urls else None
        video_filename = video_filenames[0] if video_filenames else None
        cloudfront_url = cloudfront_urls[0] if cloudfront_urls else None
        thumbnail_url = thumbnail_urls[0] if thumbnail_urls else None
    
    # URL 유효성 검증을 위한 로깅 추가
    logger.info(f"Final videoUrl: {video_url}")
    logger.info(f"Final cloudfrontUrl: {cloudfront_url}")
    logger.info(f"Final videoFilename: {video_filename}")
    
    # CloudFront URL이 실제 비디오 파일인지 확인
    if cloudfront_url and video_filename:
        # 실제 비디오 파일 URL로 설정
        final_video_url = cloudfront_url
        logger.info(f"Using CloudFront URL for video: {final_video_url}")
    elif video_url:
        # S3 URL이 있는 경우 사용
        final_video_url = video_url
        logger.info(f"Using S3 URL for video: {final_video_url}")
    else:
        final_video_url = None
        logger.warning("No valid video URL found")
    
    return {
        "ok": True,
        "executionId": result["executionId"],
        "output": last_output,
        "videoUrl": video_url,  # 첫 번째 비디오 URL (하위 호환성)
        "videoFilename": video_filename,  # 첫 번째 비디오 파일명 (하위 호환성)
        "cloudfrontUrl": cloudfront_url,  # 첫 번째 CloudFront URL (하위 호환성)
        "finalVideoUrl": final_video_url,  # 첫 번째 최종 비디오 URL (하위 호환성)
        "thumbnailUrl": thumbnail_url,  # 첫 번째 썸네일 URL (하위 호환성)
        "videoUrls": all_urls,  # 모든 비디오 URL 배열
        "videoFilenames": video_filenames,  # 모든 비디오 파일명 배열
        "cloudfrontUrls": cloudfront_urls,  # 모든 CloudFront URL 배열
        "thumbnailUrls": thumbnail_urls,  # 모든 썸네일 URL 배열
        "allOutputs": result["outputs"],
        "completionReason": result.get("completionReason") or "UNKNOWN",
    }

@app.route("/api/video/video_ai", methods=["GET", "POST", "OPTIONS"])
def video_ai():
    try:
        if request.method == "OPTIONS":
            return jsonify({"ok": True})
        ai_prompt = parse_request(request)
        logger.info("=== /api/video/video_ai === %s", ai_prompt)

        if not ai_prompt.get("prompt"):
            return jsonify({"ok": False, "error": "MISSING_PROMPT"}), 400
        if not ai_prompt.get("selectedVideo"):
            return jsonify({"ok": False, "error": "MISSING_SELECTED_VIDEO"}), 400

        payload = invoke_flow(
            flow_identifier=FLOW_IDENTIFIER,
            flow_alias_identifier=FLOW_ALIAS_IDENTIFIER,
            flow_input_node_name=FLOW_INPUT_NODE_NAME,
            ai_prompt=ai_prompt
        )
        return jsonify(to_jsonable(payload)), 200

    except ClientError as ce:
        code = getattr(ce, "response", {}).get("Error", {}).get("Code")
        msg = str(ce)
        logger.exception("ClientError: %s", msg)
        if code and "ResourceNotFoundException" in code:
            return jsonify({"ok": False, "error": "RESOURCE_NOT_FOUND", "detail": msg}), 404
        return jsonify({"ok": False, "error": "CLIENT_ERROR", "detail": msg}), 500
    except Exception as e:
        logger.exception("UnexpectedError")
        return jsonify({"ok": False, "error": "UNEXPECTED_ERROR", "detail": str(e)}), 500

# ▶️ 디버그: Flow/Alias 존재 및 매핑 확인
@app.route("/api/video/_debug/verify_flow", methods=["GET"])
def verify_flow():
    try:
        sts = boto3.client("sts").get_caller_identity()
        acct = sts.get("Account")
        runtime_region = AWS_REGION

        build = get_buildtime()
        flow = build.get_flow(flowIdentifier=FLOW_IDENTIFIER)  # 존재 확인
        alias = build.get_flow_alias(flowIdentifier=FLOW_IDENTIFIER, aliasIdentifier=FLOW_ALIAS_IDENTIFIER)  # 매핑 확인

        return jsonify({
            "ok": True,
            "whoami": {"account": acct, "region": runtime_region},
            "flow": {"id": flow.get("id"), "arn": flow.get("arn"), "status": flow.get("status", "UNKNOWN")},
            "alias": {
                "id": alias.get("id"),
                "arn": alias.get("arn"),
                "flowId": alias.get("flowId"),
                "routingConfiguration": alias.get("routingConfiguration")  # 어떤 버전에 붙었는지
            }
        }), 200
    except ClientError as ce:
        logger.exception("Verify ClientError")
        return jsonify({"ok": False, "error": "VERIFY_CLIENT_ERROR", "detail": str(ce)}), 500
    except Exception as e:
        logger.exception("Verify Unexpected")
        return jsonify({"ok": False, "error": "VERIFY_UNEXPECTED", "detail": str(e)}), 500

# 헬스체크 API
@app.route("/api/video/health", methods=["GET"])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Video AI API is running'}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
