import json
import boto3
import logging
from datetime import datetime
from typing import Dict, List, Any

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
s3_client = boto3.client('s3')

def lambda_handler(event, context):

    try:
        detail = event.get('detail', {})
        source_bucket = detail.get('bucket', {}).get('name')
        source_key = detail.get('object', {}).get('key')
        destination_bucket = source_bucket

        # 무시할 파일 패턴
        if source_key.endswith('.write_access_check_file.temp') or source_key.endswith('manifest.json'):
            logger.info(f"무시된 파일: {source_key}")
            return {
                'statusCode': 204,
                'body': json.dumps({'message': '무시된 파일', 'key': source_key}, ensure_ascii=False)
            }

        # 파일 크기 0이면 무시
        head_obj = s3_client.head_object(Bucket=source_bucket, Key=source_key)
        if head_obj['ContentLength'] == 0:
            logger.info(f"0바이트 파일 무시됨: {source_key}")
            return {
                'statusCode': 204,
                'body': json.dumps({'message': '빈 파일 무시됨', 'key': source_key}, ensure_ascii=False)
            }

        # 모든 데이터 타입의 파일들을 수집하고 처리
        combined_data = collect_and_process_all_data(source_bucket, source_key)
        
        # 합쳐진 데이터를 새로운 디렉토리에 저장
        destination_key = generate_combined_destination_key(source_key)
        save_combined_to_s3(combined_data, destination_bucket, destination_key)

        # 시간 기준 매칭된 클립 수 계산
        matched_clips_count = len(merge_metadata_by_time(
            combined_data['twelvelabs_data'],
            combined_data['transcribe_data'], 
            combined_data['yolo_data']
        ))

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': '시간 기준 데이터 매칭 및 통합 저장 완료',
                'source': f"{source_bucket}/{source_key}",
                'destination': f"{destination_bucket}/{destination_key}",
                'original_counts': {
                    'transcribe_records': len(combined_data.get('transcribe_data', [])),
                    'twelvelabs_records': len(combined_data.get('twelvelabs_data', [])),
                    'yolo_records': len(combined_data.get('yolo_data', []))
                },
                'matched_clips': matched_clips_count
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}, ensure_ascii=False)
        }

def process_data_by_type(raw_data: Dict[str, Any], data_type: str) -> List[Dict[str, Any]]:
    processors = {
        'transcribe': process_transcribe_data,
        'twelvelabs': process_twelvelabs_data,
        'yolo_opencv': process_yolo_opencv_data
    }
    processor = processors.get(data_type)
    if not processor:
        raise ValueError(f"지원하지 않는 데이터 타입: {data_type}")
    return processor(raw_data)

def process_transcribe_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transcribe JSON에서 transcript, start_time, end_time만 추출
    """
    processed_items = []
    try:
        if 'results' in data and 'items' in data['results']:
            for item in data['results']['items']:
                if item.get('type') == 'pronunciation':
                    alternatives = item.get('alternatives', [{}])
                    if alternatives:
                        processed_items.append({
                            'transcript': alternatives[0].get('content', ''),
                            'start_time': float(item.get('start_time', 0)),
                            'end_time': float(item.get('end_time', 0))
                        })
        logger.info(f"Transcribe 데이터 처리 완료: {len(processed_items)}개 항목")
        return processed_items
    except Exception as e:
        logger.error(f"Transcribe 처리 오류: {str(e)}")
        raise

def process_twelvelabs_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    TwelveLabs JSON에서 embedding, startSec, endSec만 추출
    """
    processed_items = []
    try:
        segments = data.get('data', [data]) if isinstance(data.get('data'), list) else [data]
        for segment in segments:
            embedding = segment.get('embedding', [])
            if isinstance(embedding, str):
                try:
                    embedding = json.loads(embedding)
                except:
                    embedding = []
            processed_items.append({
                'embedding': embedding,
                'startSec': float(segment.get('startSec', 0)),
                'endSec': float(segment.get('endSec', 0))
            })
        logger.info(f"TwelveLabs 처리 완료: {len(processed_items)}개 항목")
        return processed_items
    except Exception as e:
        logger.error(f"TwelveLabs 처리 오류: {str(e)}")
        raise

def process_yolo_opencv_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    YOLO/OpenCV JSON에서 timestamp_seconds, class_name만 추출
    {"results": [{"frame_id": 0, "timestamp_seconds": 0.0, "detections": [...]}]}
    """
    processed_items = []
    try:
        # 새로운 형식: results 배열이 있는 경우
        if 'results' in data:
            results = data['results']
            if isinstance(results, list):
                for result in results:
                    frame_id = result.get('frame_id', 0)
                    timestamp_seconds = float(result.get('timestamp_seconds', 0))
                    detections = result.get('detections', [])
                    
                    for detection in detections:
                        processed_items.append({
                            'timestamp_seconds': timestamp_seconds,
                            'class_name': detection.get('class_name', '')
                        })
        
        # 기존 형식 지원 - 단일 프레임 데이터 처리
        elif 'frame_id' in data and 'timestamp_seconds' in data and 'detections' in data:
            timestamp_seconds = float(data.get('timestamp_seconds', 0))
            detections = data.get('detections', [])
            
            for detection in detections:
                processed_items.append({
                    'timestamp_seconds': timestamp_seconds,
                    'class_name': detection.get('class_name', '')
                })
        
        # 기존 형식 지원 - 다중 프레임 데이터 처리 (frames 배열이 있는 경우)
        elif 'frames' in data:
            for frame in data['frames']:
                timestamp_seconds = float(frame.get('timestamp_seconds', 0))
                detections = frame.get('detections', [])
                
                for detection in detections:
                    processed_items.append({
                        'timestamp_seconds': timestamp_seconds,
                        'class_name': detection.get('class_name', '')
                    })
        
        # 기존 형식 지원 - detections 배열만 있는 경우
        elif 'detections' in data:
            detections = data['detections']
            for detection in detections:
                processed_items.append({
                    'timestamp_seconds': float(detection.get('timestamp_seconds', 0)),
                    'class_name': detection.get('class_name', '')
                })
        
        logger.info(f"YOLO/OpenCV 처리 완료: {len(processed_items)}개 항목")
        return processed_items
    except Exception as e:
        logger.error(f"YOLO/OpenCV 처리 오류: {str(e)}")
        raise

def collect_and_process_all_data(bucket: str, triggered_key: str) -> Dict[str, Any]:
    """
    S3에서 모든 데이터 타입의 파일들을 수집하고 처리하여 하나로 합침
    """
    combined_data = {
        'transcribe_data': [],
        'twelvelabs_data': [],
        'yolo_data': []
    }
    
    try:
        # 각 데이터 타입별 디렉토리에서 파일들 수집
        data_types = [
            ('transcribe/', 'transcribe'),
            ('twelvelabs/', 'twelvelabs'),
            ('yolo/', 'yolo_opencv'),
            ('yolo_opencv/', 'yolo_opencv'),
            ('marengo_data/', 'twelvelabs')
        ]
        
        for prefix, data_type in data_types:
            try:
                # S3에서 해당 prefix의 파일들 나열
                response = s3_client.list_objects_v2(
                    Bucket=bucket,
                    Prefix=prefix
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        
                        # 디렉토리나 무시할 파일 건너뛰기
                        if (key.endswith('/') or 
                            key.endswith('.write_access_check_file.temp') or 
                            key.endswith('manifest.json') or
                            obj['Size'] == 0):
                            continue
                        
                        try:
                            # 파일 내용 읽기
                            file_response = s3_client.get_object(Bucket=bucket, Key=key)
                            raw_data = json.loads(file_response['Body'].read().decode('utf-8'))
                            
                            # 데이터 처리
                            processed_data = process_data_by_type(raw_data, data_type)
                            
                            # 데이터 타입별로 분류하여 저장
                            if data_type == 'transcribe':
                                combined_data['transcribe_data'].extend(processed_data)
                            elif data_type == 'twelvelabs':
                                combined_data['twelvelabs_data'].extend(processed_data)
                            elif data_type == 'yolo_opencv':
                                combined_data['yolo_data'].extend(processed_data)
                                
                            logger.info(f"처리 완료: {key} ({len(processed_data)}개 항목)")
                            
                        except Exception as e:
                            logger.warning(f"파일 처리 실패: {key}, 오류: {str(e)}")
                            continue
                            
            except Exception as e:
                logger.warning(f"디렉토리 처리 실패: {prefix}, 오류: {str(e)}")
                continue
        
        logger.info(f"전체 데이터 수집 완료 - Transcribe: {len(combined_data['transcribe_data'])}, "
                   f"TwelveLabs: {len(combined_data['twelvelabs_data'])}, "
                   f"YOLO: {len(combined_data['yolo_data'])}")
        
        return combined_data
        
    except Exception as e:
        logger.error(f"데이터 수집 중 오류: {str(e)}")
        raise

def generate_combined_destination_key(source_key: str) -> str:
    """
    통합된 데이터를 저장할 새로운 경로 생성
    """
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return f"combined_data/integrated_data_{timestamp}.json"

def merge_metadata_by_time(twelvelabs_data: List[Dict], transcribe_data: List[Dict], yolo_data: List[Dict]) -> List[Dict]:
    """
    TwelveLabs의 startSec, endSec을 기준으로 시간이 일치하는 데이터들을 매칭하여 통합
    """
    refined_clips = []
    
    try:
        logger.info(f"매칭 시작 - TwelveLabs: {len(twelvelabs_data)}, Transcribe: {len(transcribe_data)}, YOLO: {len(yolo_data)}")
        
        # TwelveLabs 데이터가 없는 경우, Transcribe 데이터만으로 클립 생성
        if not twelvelabs_data and transcribe_data:
            logger.info("TwelveLabs 데이터가 없어서 Transcribe 데이터만으로 클립 생성")
            
            # Transcribe 데이터를 시간순으로 정렬
            sorted_transcribe = sorted(transcribe_data, key=lambda x: x['start_time'])
            
            for word_info in sorted_transcribe:
                word_start = word_info['start_time']
                word_end = word_info['end_time']
                
                # YOLO 데이터에서 시간이 겹치는 객체 찾기
                clip_objects = []
                for obj_info in yolo_data:
                    obj_timestamp = obj_info['timestamp_seconds']
                    
                    # 객체의 타임스탬프가 단어 시간 범위 안에 있는 경우
                    if word_start <= obj_timestamp <= word_end:
                        clip_objects.append(obj_info['class_name'])
                
                # 클립 생성
                refined_clip = {
                    "startSec": word_start,
                    "endSec": word_end,
                    "embedding": [],  # TwelveLabs 데이터가 없으므로 빈 배열
                    "transcript": word_info['transcript'],
                    "detectedObjects": list(set(clip_objects))  # 중복 제거
                }
                
                refined_clips.append(refined_clip)
        
        # TwelveLabs 데이터가 있는 경우 기존 로직 사용
        else:
            for clip in twelvelabs_data:
                master_start = clip['startSec']
                master_end = clip['endSec']
                
                logger.info(f"클립 처리 중: {master_start}초 ~ {master_end}초")
                
                # Transcribe 데이터에서 시간 범위에 포함되는 대본 찾기
                clip_transcript = ""
                matched_words = 0
                for word_info in transcribe_data:
                    word_start = word_info['start_time']
                    word_end = word_info['end_time']
                    
                    # 단어의 시작과 끝이 기준 시간 안에 완전히 들어오는 경우
                    if word_start >= master_start and word_end <= master_end:
                        clip_transcript += word_info['transcript'] + " "
                        matched_words += 1
                
                logger.info(f"매칭된 단어 수: {matched_words}")
                
                # YOLO 데이터에서 시간이 겹치는 객체 찾기
                clip_objects = []
                matched_objects = 0
                for obj_info in yolo_data:
                    obj_timestamp = obj_info['timestamp_seconds']
                    
                    # 객체의 타임스탬프가 기준 시간 범위 안에 있는 경우
                    if master_start <= obj_timestamp <= master_end:
                        clip_objects.append(obj_info['class_name'])
                        matched_objects += 1
                
                logger.info(f"매칭된 객체 수: {matched_objects}")
                
                # 모든 정보를 하나로 합침 (중복 제거)
                refined_clip = {
                    "startSec": master_start,
                    "endSec": master_end,
                    "embedding": clip['embedding'],
                    "transcript": clip_transcript.strip(),
                    "detectedObjects": list(set(clip_objects))  # 중복 제거
                }
                
                refined_clips.append(refined_clip)
        
        logger.info(f"시간 기준 데이터 매칭 완료: {len(refined_clips)}개 클립")
        return refined_clips
        
    except Exception as e:
        logger.error(f"데이터 매칭 중 오류: {str(e)}")
        raise

def save_combined_to_s3(combined_data: Dict[str, Any], bucket: str, key: str) -> None:
    """
    시간 기준으로 매칭된 통합 데이터를 S3의 새로운 디렉토리에 저장
    """
    try:
        logger.info(f"데이터 매칭 시작 - 원본 데이터 수: Transcribe={len(combined_data['transcribe_data'])}, TwelveLabs={len(combined_data['twelvelabs_data'])}, YOLO={len(combined_data['yolo_data'])}")
        
        # 시간 기준으로 데이터 매칭
        matched_clips = merge_metadata_by_time(
            combined_data['twelvelabs_data'],
            combined_data['transcribe_data'], 
            combined_data['yolo_data']
        )
        
        logger.info(f"매칭 완료 - 생성된 클립 수: {len(matched_clips)}")
        
        # 최종 통합 데이터 구조 생성
        integrated_data = {
            'processed_at': datetime.utcnow().isoformat(),
            'total_clips': len(matched_clips),
            'original_counts': {
                'transcribe_records': len(combined_data['transcribe_data']),
                'twelvelabs_records': len(combined_data['twelvelabs_data']),
                'yolo_records': len(combined_data['yolo_data'])
            },
            'matched_clips': matched_clips
        }
        
        # 디버깅을 위해 첫 번째 클립 정보 로그
        if matched_clips:
            logger.info(f"첫 번째 클립 샘플: {json.dumps(matched_clips[0], ensure_ascii=False)}")
        
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(integrated_data, ensure_ascii=False, indent=2),
            ContentType='application/json'
        )
        logger.info(f"시간 매칭된 통합 데이터 S3 저장 완료: {bucket}/{key}")
        
    except Exception as e:
        logger.error(f"통합 데이터 S3 저장 오류: {str(e)}")
        raise
