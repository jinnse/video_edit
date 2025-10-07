import json
import boto3
import os
import time
import re
from datetime import datetime
from typing import Optional

# ===================== 하드코딩된 설정값 =====================
VIDEO_BUCKET = "video-input-pipeline-20250724"
SOURCE_BUCKET_DEFAULT = VIDEO_BUCKET
DEFAULT_PREFIX = "original/"
OUTPUT_PREFIX = "output/"
THUMBNAIL_PREFIX = "thumbnails/"
PRESIGNED_EXPIRE_SEC = 3600
THUMBNAIL_ENABLED = True
THUMBNAIL_TIME = 1
MEDIACONVERT_ROLE_ARN = "arn:aws:iam::567279714866:role/MediaConvertServiceRole"

# 인덱스 패턴 (media_th.py에서 가져옴)
INDEXED_JPG_PATTERN = re.compile(r'^([^/]+?)\.(\d+)\.jpg$', re.IGNORECASE)

# ===================== 유틸리티 함수 =====================
def ensure_prefix(p: str) -> str:
    return p if p.endswith("/") else (p + "/")

def parse_time_to_seconds(time_str):
    if time_str is None or time_str == "":
        return 0.0
    s = str(time_str)
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 3:
            h, m, sec = int(parts[0]), int(parts[1]), float(parts[2])
            return h*3600 + m*60 + sec
        if len(parts) == 2:
            m, sec = int(parts[0]), float(parts[1])
            return m*60 + sec
    return float(s)

def seconds_to_time_format(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def seconds_to_timecode(seconds, fps=29.97):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    # 프레임을 0으로 고정하여 더 안전하게 처리
    frames = 0
    # 더 안전한 형식: HH:MM:SS:FF
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"

def error_json(msg, action_group="default", function_name="default", details=None):
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function_name,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": json.dumps({
                            "success": False,
                            "error": msg,
                            "details": details
                        }, ensure_ascii=False)
                    }
                }
            }
        }
    }

# ===================== 파일명 관련 함수 =====================
def sanitize_basename(name: str) -> str:
    import re
    name = name.replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "", name) or "video"

def build_output_names(base_name: str, start_s: float, end_s: float, ts_str: str):
    base = sanitize_basename(base_name)
    start_i, end_i = int(start_s), int(end_s)
    range_suffix = f"_{start_i}s-{end_i}s"
    
    out_name = f"{base}{range_suffix}.mp4"
    thumb_name = f"{base}{range_suffix}.jpg"
    
    return out_name, thumb_name

# ===================== S3 관련 함수 =====================
def extract_source_from_prompt(prompt_text: str):
    text = prompt_text or ""
    
    # 1) s3 URI
    m = re.search(r's3://([^/\s]+)/(?:\s*)?([^\s"\'<>]+)', text)
    if m:
        bucket = m.group(1).strip()
        key = m.group(2).strip()
        print(f"✅ s3 URI 감지: bucket={bucket}, key={key}")
        return bucket, key
    
    # 2) parameters에서 video_input 찾기
    if "parameters" in text or "video_input" in text:
        video_match = re.search(r'"video_input"\s*:\s*"([^"]+)"', text)
        if video_match:
            video_file = video_match.group(1).strip()
            # 파일명에 경로가 없으면 기본 경로 추가
            if not "/" in video_file and not video_file.startswith(DEFAULT_PREFIX):
                video_file = f"{DEFAULT_PREFIX}{video_file}"
            print(f"✅ parameters에서 video_input 감지: key={video_file}")
            return SOURCE_BUCKET_DEFAULT, video_file
    
    # 3) 일반적인 비디오 파일 확장자로 끝나는 파일명 찾기
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    for ext in video_extensions:
        pattern = rf'([^/\s"\'<>]+{re.escape(ext)})'
        matches = re.findall(pattern, text)
        if matches:
            video_file = matches[0].strip()
            # 파일명에 경로가 없으면 기본 경로 추가
            if not "/" in video_file and not video_file.startswith(DEFAULT_PREFIX):
                video_file = f"{DEFAULT_PREFIX}{video_file}"
            print(f"✅ 비디오 파일 확장자 감지: key={video_file}")
            return SOURCE_BUCKET_DEFAULT, video_file
    
    # 4) 토큰들에서 경로/파일처럼 보이는 후보 찾기 (더 엄격한 조건)
    tokens = re.findall(r'([^\s"\'<>]+)', text)
    for t in reversed(tokens):
        # 파일명이 확장자를 가지고 있고, 특수문자가 적은 경우만 선택
        if "." in t and len(t) > 3 and len(t) < 100:
            # 한글이나 특수문자가 많이 포함된 경우 제외
            if not re.search(r'[가-힣]{3,}', t) and not re.search(r'[^\w\-_.]', t):
                cleaned = t.strip()
                print(f"✅ 경로/파일 토큰 감지: key={cleaned}")
                return SOURCE_BUCKET_DEFAULT, cleaned
    
    # 5) fallback - 기본값 사용
    print(f"⚠️ 키 감지 실패 → 기본값 사용")
    return SOURCE_BUCKET_DEFAULT, f"{DEFAULT_PREFIX}video.mp4"

def s3_key_exists(bucket: str, key: str) -> bool:
    s3 = boto3.client("s3")
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        print(f"ℹ️ head_object 실패: s3://{bucket}/{key} ({e})")
        return False

def generate_presigned_url(bucket, key, expiration):
    s3 = boto3.client("s3")
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=int(expiration)
        )
    except Exception as e:
        print(f"❌ Presigned URL 생성 오류: {e}")
        return None

# ===================== MediaConvert 관련 함수 =====================
def cut_video_with_mediaconvert(input_s3_uri, output_s3_uri, start_seconds, duration_seconds, output_filename):
    print(f"🎬 MediaConvert 영상 자르기 시작: {start_seconds}s ~ {start_seconds + duration_seconds}s")
    
    mediaconvert = boto3.client('mediaconvert', region_name='ap-northeast-2')
    
    # 시간 코드 변환
    start_timecode = seconds_to_timecode(start_seconds)
    end_timecode = seconds_to_timecode(start_seconds + duration_seconds)
    
    # 출력 파일명에서 확장자 제거
    base_filename = output_filename.replace('.mp4', '')
    
    job_settings = {
        "TimecodeConfig": {
            "Source": "ZEROBASED"
        },
        "Inputs": [
            {
                "FileInput": input_s3_uri,
                "TimecodeSource": "ZEROBASED",
                "InputClippings": [
                    {
                        "StartTimecode": seconds_to_timecode(start_seconds),
                        "EndTimecode": seconds_to_timecode(start_seconds + duration_seconds)
                    }
                ],
                "AudioSelectors": {
                    "Audio Selector 1": {
                        "DefaultSelection": "DEFAULT"
                    }
                }
            }
        ],
        "OutputGroups": [
            {
                "Name": "File Group",
                "OutputGroupSettings": {
                    "Type": "FILE_GROUP_SETTINGS",
                    "FileGroupSettings": {
                        "Destination": output_s3_uri.replace(f"/{output_filename}", "/")
                    }
                },
                "Outputs": [
                    {
                        "NameModifier": f"_{int(start_seconds)}s-{int(start_seconds + duration_seconds)}s",
                        "VideoDescription": {
                            "CodecSettings": {
                                "Codec": "H_264",
                                "H264Settings": {
                                    "RateControlMode": "QVBR",
                                    "QvbrSettings": {
                                        "QvbrQualityLevel": 8
                                    },
                                    "MaxBitrate": 5000000,
                                    "AdaptiveQuantization": "HIGH",
                                    "EntropyEncoding": "CABAC",
                                    "FramerateControl": "INITIALIZE_FROM_SOURCE",
                                    "FramerateConversionAlgorithm": "DUPLICATE_DROP",
                                    "CodecProfile": "MAIN",
                                    "SlowPal": "DISABLED",
                                    "SpatialAdaptiveQuantization": "ENABLED",
                                    "Syntax": "DEFAULT",
                                    "TemporalAdaptiveQuantization": "ENABLED"
                                }
                            }
                        },
                        "AudioDescriptions": [
                            {
                                "AudioSourceName": "Audio Selector 1",
                                "CodecSettings": {
                                    "Codec": "AAC",
                                    "AacSettings": {
                                        "CodecProfile": "LC",
                                        "RateControlMode": "CBR",
                                        "Bitrate": 128000,
                                        "SampleRate": 48000,
                                        "RawFormat": "NONE",
                                        "Specification": "MPEG4",
                                        "CodingMode": "CODING_MODE_2_0"
                                    }
                                }
                            }
                        ],
                        "ContainerSettings": {
                            "Container": "MP4",
                            "Mp4Settings": {
                                "CslgAtom": "INCLUDE",
                                "FreeSpaceBox": "EXCLUDE",
                                "MoovPlacement": "PROGRESSIVE_DOWNLOAD"
                            }
                        }
                    }
                ]
            }
        ]
    }
    
    try:
        response = mediaconvert.create_job(
            Role=MEDIACONVERT_ROLE_ARN,
            Settings=job_settings,
            StatusUpdateInterval='SECONDS_10',
            UserMetadata={
                'start_time': str(start_seconds),
                'duration': str(duration_seconds),
                'output_filename': output_filename
            }
        )
        
        job_id = response['Job']['Id']
        print(f"✅ MediaConvert Job 생성 성공: {job_id}")
        return True, job_id
        
    except Exception as e:
        print(f"❌ MediaConvert Job 생성 실패: {e}")
        return False, None

def wait_for_mediaconvert_job(job_id, timeout_seconds=300):
    print(f"⏳ MediaConvert Job 완료 대기: {job_id}")
    mediaconvert = boto3.client('mediaconvert', region_name='ap-northeast-2')
    
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            response = mediaconvert.get_job(Id=job_id)
            status = response['Job']['Status']
            
            if status == 'COMPLETE':
                print(f"✅ MediaConvert Job 완료: {job_id}")
                return True
            elif status == 'ERROR':
                error_message = response['Job'].get('ErrorMessage', 'Unknown error')
                print(f"❌ MediaConvert Job 실패: {error_message}")
                return False
            elif status in ['SUBMITTED', 'PROGRESSING']:
                print(f"⏳ MediaConvert Job 진행 중: {status}")
                time.sleep(10)
            else:
                print(f"⚠️ MediaConvert Job 상태: {status}")
                time.sleep(10)
                
        except Exception as e:
            print(f"❌ MediaConvert Job 상태 확인 실패: {e}")
            return False
    
    print(f"⏰ MediaConvert Job 타임아웃: {job_id}")
    return False

def generate_thumbnail_with_mediaconvert(input_s3_uri, output_s3_uri, timestamp_seconds, output_filename, original_video_base_name):
    if not THUMBNAIL_ENABLED:
        return False, None
    
    print(f"🖼️ MediaConvert 썸네일 생성: {timestamp_seconds}s")
    
    mediaconvert = boto3.client('mediaconvert', region_name='ap-northeast-2')
    
    # 시간 코드 변환
    thumbnail_timecode = seconds_to_timecode(timestamp_seconds)
    
    # 출력 파일명에서 확장자 제거
    scene_specific_base_name = output_filename.replace('.jpg', '') # e.g., soccer_16s-40s
    
    # NameModifier는 원본 비디오 파일명 뒤에 붙으므로, 
    # scene_specific_base_name에서 original_video_base_name을 제거한 나머지를 사용
    # 예: soccer_10s-35s에서 soccer를 제거하면 _10s-35s가 됨
    if scene_specific_base_name.startswith(original_video_base_name):
        name_modifier_suffix = scene_specific_base_name[len(original_video_base_name):]
    else:
        name_modifier_suffix = f"_{scene_specific_base_name}"
    
    # S3 URI에서 버킷과 프리픽스 추출 (더 안전한 방법)
    uri_parts = output_s3_uri.replace('s3://', '').split('/')
    output_bucket = uri_parts[0]  # bucket
    out_prefix = '/'.join(uri_parts[1:-1]) + '/' if len(uri_parts) > 2 else ''  # prefix/
    
    job_settings = {
        "TimecodeConfig": {
            "Source": "ZEROBASED"
        },
        "Inputs": [
            {
                "FileInput": input_s3_uri,
                "TimecodeSource": "ZEROBASED",
                "InputClippings": [
                    {
                        "StartTimecode": thumbnail_timecode,
                        "EndTimecode": seconds_to_timecode(timestamp_seconds + 0.1)
                    }
                ]
            }
        ],
        "OutputGroups": [
            # 임시 비디오 출력 (MediaConvert 요구사항)
            {
                "Name": "File Group",
                "OutputGroupSettings": {
                    "Type": "FILE_GROUP_SETTINGS",
                    "FileGroupSettings": {
                        "Destination": f"s3://{output_bucket}/{out_prefix}"
                    }
                },
                "Outputs": [
                    {
                        "NameModifier": f"_{int(timestamp_seconds)}s",
                        "VideoDescription": {
                            "CodecSettings": {
                                "Codec": "H_264",
                                "H264Settings": {
                                    "RateControlMode": "QVBR",
                                    "QvbrSettings": {
                                        "QvbrQualityLevel": 8
                                    },
                                    "MaxBitrate": 5000000,
                                    "AdaptiveQuantization": "HIGH",
                                    "EntropyEncoding": "CABAC",
                                    "FramerateControl": "INITIALIZE_FROM_SOURCE",
                                    "FramerateConversionAlgorithm": "DUPLICATE_DROP",
                                    "CodecProfile": "MAIN",
                                    "SlowPal": "DISABLED",
                                    "SpatialAdaptiveQuantization": "ENABLED",
                                    "Syntax": "DEFAULT",
                                    "TemporalAdaptiveQuantization": "ENABLED"
                                }
                            }
                        },
                        "AudioDescriptions": [],
                        "ContainerSettings": {
                            "Container": "MP4",
                            "Mp4Settings": {
                                "CslgAtom": "INCLUDE",
                                "FreeSpaceBox": "EXCLUDE",
                                "MoovPlacement": "PROGRESSIVE_DOWNLOAD"
                            }
                        }
                    }
                ]
            },
            # 썸네일 출력
            {
                "Name": "Thumbnail",
                "OutputGroupSettings": {
                    "Type": "FILE_GROUP_SETTINGS",
                    "FileGroupSettings": {
                        "Destination": output_s3_uri.replace(f"/{output_filename}", "/")
                    }
                },
                "Outputs": [
                    {
                        "NameModifier": name_modifier_suffix,
                        "Extension": "jpg",
                        "ContainerSettings": {"Container": "RAW"},
                        "VideoDescription": {
                            "CodecSettings": {
                                "Codec": "FRAME_CAPTURE",
                                "FrameCaptureSettings": {
                                    "FramerateNumerator": 1,
                                    "FramerateDenominator": 1,
                                    "MaxCaptures": 1,
                                    "Quality": 80
                                }
                            }
                        }
                    }
                ]
            }
        ]
    }
    
    try:
        response = mediaconvert.create_job(
            Role=MEDIACONVERT_ROLE_ARN,
            Settings=job_settings,
            StatusUpdateInterval='SECONDS_10',
            UserMetadata={
                'timestamp': str(timestamp_seconds),
                'output_filename': output_filename
            }
        )
        
        job_id = response['Job']['Id']
        print(f"✅ MediaConvert 썸네일 Job 생성 성공: {job_id}")
        return True, job_id
        
    except Exception as e:
        print(f"❌ MediaConvert 썸네일 Job 생성 실패: {e}")
        return False, None

def find_indexed_thumbnail(bucket: str, prefix: str, base: str) -> Optional[str]:
    """
    thumbnails/ 아래에서 <base>.<숫자>.jpg 를 찾아 키를 반환.
    없으면 None.
    """
    target_prefix = f"{prefix}{base}"
    # 예: thumbnails/soccer_0s-45s 로 시작하는 객체들 검색
    s3 = boto3.client("s3")
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=target_prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']  # thumbnails/soccer_0s-45s.0000000.jpg
            filename = key[len(prefix):]  # soccer_0s-45s.0000000.jpg
            if INDEXED_JPG_PATTERN.match(filename):
                print(f"🔎 인덱스 썸네일 발견: s3://{bucket}/{key}")
                return key
    print(f"⚠️ 인덱스 썸네일을 못 찾음: s3://{bucket}/{prefix}{base}.<num>.jpg")
    return None

def rename_indexed_thumbnail(bucket: str, base_name: str, indexed_key: str) -> bool:
    """
    s3://<bucket>/thumbnails/<base>.<번호>.jpg → s3://<bucket>/thumbnails/<base>.jpg 로 리네임(copy→delete)
    """
    final_key = f"{THUMBNAIL_PREFIX}{base_name}.jpg"
    print(f"🖼️ Rename thumbnail: s3://{bucket}/{indexed_key} → s3://{bucket}/{final_key}")
    try:
        s3 = boto3.client("s3")
        s3.copy(
            CopySource={"Bucket": bucket, "Key": indexed_key},
            Bucket=bucket,
            Key=final_key
        )
        s3.delete_object(Bucket=bucket, Key=indexed_key)
        print("✅ Renamed (copy→delete) complete")
        return True
    except Exception as e:
        print(f"❌ Rename failed: {e}")
        return False

# ===================== 메인 핸들러 =====================
def lambda_handler(event, context):
    try:
        print("🚀 영상 자르기 Lambda 시작")
        print(json.dumps(event, indent=2, ensure_ascii=False))
        
        start_time = time.time()
        
        action_group = event.get("actionGroup", "default")
        function_name = event.get("function", "default")
        input_text = event.get("inputText", "")
        
        # 액션 파라미터 추출
        params = {}
        if "parameters" in event:
            for p in event["parameters"]:
                params[p.get("name", "")] = p.get("value", "")
        
        # 입력 데이터 처리 (parameters 또는 JSON)
        scenes_to_process = []
        
        # 1) parameters에서 개별 장면 처리
        if params and "start_time" in params and "end_time" in params:
            start_time = parse_time_to_seconds(params.get("start_time"))
            end_time = parse_time_to_seconds(params.get("end_time"))
            
            if start_time >= 0 and end_time > start_time:
                scenes_to_process.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "video_input": params.get("video_input", "soccer.mp4")
                })
                print(f"✅ parameters에서 장면 감지: {start_time}s ~ {end_time}s")
        
        # 2) JSON에서 scenes 배열 처리
        if not scenes_to_process:
            try:
                if input_text.strip().startswith('```json'):
                    # JSON 블록에서 추출
                    json_match = re.search(r'```json\s*(.*?)\s*```', input_text, re.DOTALL)
                    if json_match:
                        input_data = json.loads(json_match.group(1))
                        scenes_to_process = input_data.get("scenes", [])
                        print(f"✅ JSON 블록에서 {len(scenes_to_process)}개 장면 감지")
                else:
                    # 직접 JSON 파싱
                    input_data = json.loads(input_text)
                    scenes_to_process = input_data.get("scenes", [])
                    print(f"✅ JSON에서 {len(scenes_to_process)}개 장면 감지")
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON 파싱 실패: {e}")
        
        # 3) 장면이 없으면 오류
        if not scenes_to_process:
            return error_json("처리할 장면이 없습니다. start_time/end_time 파라미터 또는 scenes 배열이 필요합니다.", action_group, function_name)
        
        print(f"📋 처리할 장면 수: {len(scenes_to_process)}")
        
        # --- 프롬프트에서 (source_bucket, source_key) 추출 ---
        source_bucket, source_key = extract_source_from_prompt(input_text)
        
        # 키 감지 실패 시 기본값 사용
        if source_bucket is None or source_key is None:
            print(f"⚠️ 키 감지 실패 → 기본값 사용")
            source_bucket = SOURCE_BUCKET_DEFAULT
            source_key = f"{DEFAULT_PREFIX}video.mp4"
        
        # S3 경로/버킷 (출력은 VIDEO_BUCKET)
        output_bucket = VIDEO_BUCKET
        out_prefix = ensure_prefix(OUTPUT_PREFIX)
        thumb_prefix = ensure_prefix(THUMBNAIL_PREFIX)
        
        # 로컬 파일 경로
        uid = str(int(time.time()))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name, _ = os.path.splitext(os.path.basename(source_key))
        base_name = base_name or "video"
        
        in_path = f"/tmp/input_{uid}.mp4"
        out_path = f"/tmp/output_{uid}.mp4"
        thumb_path = f"/tmp/thumb_{uid}.jpg"
        
        # 입력 S3 URI
        input_s3_uri = f"s3://{source_bucket}/{source_key}"
        
        # 장면별 처리
        processed_scenes = []
        
        for i, scene in enumerate(scenes_to_process):
            print(f"\n🎬 장면 {i+1} 처리 시작...")
            
            # 장면 정보 추출
            scene_start = parse_time_to_seconds(scene.get("start_time"))
            scene_end = parse_time_to_seconds(scene.get("end_time"))
            scene_duration = scene_end - scene_start
            
            if scene_duration <= 0:
                print(f"⚠️ 장면 {i+1} 건너뜀: 잘못된 시간 범위")
                continue
            
            # 출력 파일명 생성 (장면별로 고유한 이름)
            scene_out_name, scene_thumb_name = build_output_names(
                base_name, 
                scene_start, 
                scene_end, 
                ts
            )
            
            scene_out_key = f"{out_prefix}{scene_out_name}"
            scene_out_path = f"/tmp/output_scene{i+1}_{uid}.mp4"
            
            # 출력 S3 URI
            output_s3_uri = f"s3://{output_bucket}/{scene_out_key}"
            
            # 1) MediaConvert로 영상 자르기
            success, job_id = cut_video_with_mediaconvert(
                input_s3_uri,
                output_s3_uri,
                scene_start,
                scene_duration,
                scene_out_name
            )
            
            if not success:
                print(f"❌ 장면 {i+1} MediaConvert Job 생성 실패")
                continue
            
            # 2) Job 완료 대기
            if not wait_for_mediaconvert_job(job_id):
                print(f"❌ 장면 {i+1} MediaConvert Job 실패")
                continue
            
            # 3) 파일 크기 확인
            try:
                s3 = boto3.client("s3")
                response = s3.head_object(Bucket=output_bucket, Key=scene_out_key)
                file_size = response['ContentLength']
                print(f"📄 출력 파일명: {scene_out_name}")
                print(f"📄 출력 파일 크기: {file_size:,} bytes")
            except Exception as e:
                print(f"⚠️ 파일 크기 확인 실패: {e}")
                print(f"⚠️ 장면 {i+1} MediaConvert 결과 다운로드 실패")
                continue
            
            # 4) 썸네일 생성 (옵션)
            scene_thumb_url = None
            if THUMBNAIL_ENABLED:
                thumbnail_time = min(int(float(THUMBNAIL_TIME)), int(scene_duration * 0.5))
                thumbnail_s3_uri = f"s3://{output_bucket}/{thumb_prefix}{scene_thumb_name}"
                
                thumbnail_success, thumbnail_job_id = generate_thumbnail_with_mediaconvert(
                    input_s3_uri, 
                    thumbnail_s3_uri, 
                    scene_start + thumbnail_time, 
                    scene_thumb_name,
                    base_name # Pass the original base_name (e.g., "soccer")
                )
                
                if thumbnail_success:
                    print(f"✅ 장면 {i+1} MediaConvert 썸네일 Job 생성 성공: {thumbnail_job_id}")
                    
                    # 썸네일 Job 완료 대기
                    if wait_for_mediaconvert_job(thumbnail_job_id):
                        print(f"✅ 장면 {i+1} MediaConvert 썸네일 Job 완료: {thumbnail_job_id}")
                        
                        # 임시 비디오 파일 삭제 (MediaConvert NameModifier 규칙에 맞춤)
                        temp_video_name = f"{base_name}_{int(scene_start + thumbnail_time)}s.mp4"
                        temp_video_key = f"{thumb_prefix}{temp_video_name}"  # thumbnails/ 폴더에서 삭제
                        try:
                            s3 = boto3.client("s3")
                            s3.delete_object(Bucket=output_bucket, Key=temp_video_key)
                            print(f"🗑️ 임시 비디오 파일 삭제: {temp_video_key}")
                        except Exception as e:
                            print(f"⚠️ 임시 비디오 파일 삭제 실패: {e}")
                        
                        # 썸네일 리네임 과정 추가
                        scene_thumb_base = scene_thumb_name.replace('.jpg', '')
                        indexed_key = find_indexed_thumbnail(output_bucket, thumb_prefix, scene_thumb_base)
                        
                        if indexed_key:
                            if rename_indexed_thumbnail(output_bucket, scene_thumb_base, indexed_key):
                                print(f"✅ 장면 {i+1} 썸네일 리네임 완료")
                                tkey = f"{thumb_prefix}{scene_thumb_name}"
                                scene_thumb_url = generate_presigned_url(output_bucket, tkey, PRESIGNED_EXPIRE_SEC)
                            else:
                                print(f"❌ 장면 {i+1} 썸네일 리네임 실패")
                        else:
                            print(f"⚠️ 장면 {i+1} 인덱스 썸네일을 찾을 수 없음")
                    else:
                        print(f"❌ 장면 {i+1} MediaConvert 썸네일 Job 실패")
                else:
                    print(f"⚠️ 장면 {i+1} MediaConvert 썸네일 생성 실패")

            # presigned URL 생성
            scene_video_url = generate_presigned_url(output_bucket, scene_out_key, PRESIGNED_EXPIRE_SEC)
            scene_size_mb = file_size / (1024 * 1024)
            
            # 장면 정보 저장
            processed_scenes.append({
                "scene_number": i + 1,
                "video_url": scene_video_url,
                "thumbnail_url": scene_thumb_url,
                "filename": scene_out_name,
                "start_time": seconds_to_time_format(scene_start),
                "end_time": seconds_to_time_format(scene_end),
                "duration": seconds_to_time_format(scene_duration),
                "file_size": f"{scene_size_mb:.1f}MB",
                "output_key": scene_out_key,
                "job_id": job_id
            })
            
            print(f"✅ 장면 {i+1} 처리 완료: {scene_out_name}")

        # 6) 성공 응답
        final_time = time.time()
        print(f"⏱️ 전체 처리 시간: {final_time - start_time:.2f}초")
        
        resp = {
            "success": True,
            "total_scenes": len(processed_scenes),
            "scenes": processed_scenes,
            "source_bucket": source_bucket,
            "source_key": source_key,
            "bucket": output_bucket,
            "processing_method": "MediaConvert",
            "message": f"영상 자르기 완료! 총 {len(processed_scenes)}개 장면 처리 - MediaConvert 사용"
        }
        print(json.dumps(resp, indent=2, ensure_ascii=False))

        # 상세한 응답 메시지 생성
        scene_details = []
        for i, scene in enumerate(processed_scenes):
            scene_details.append(f"{i+1}. {scene['filename']} ({scene['start_time']} ~ {scene['end_time']}, {scene['duration']})")
        
        response_message = f"""영상 자르기 완료! 총 {len(processed_scenes)}개 장면이 생성되었습니다.

생성된 파일 목록:
{chr(10).join(scene_details)}

모든 파일은 S3 버킷 '{output_bucket}'의 '{OUTPUT_PREFIX}' 폴더에 저장되었습니다.
파일명 형식: [원본파일명]_[시작시간]s-[종료시간]s.mp4"""

        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "function": function_name,
                "functionResponse": {
                    "responseBody": { 
                        "TEXT": { 
                            "body": response_message
                        }
                    }
                }
            }
        }

    except Exception as e:
        import traceback
        print("❌ Lambda 오류:", e)
        print(traceback.format_exc())
        return error_json("Lambda 함수 실행 오류", event.get("actionGroup","default"),
                          event.get("function","default"), str(e))
