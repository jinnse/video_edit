from flask import Flask, jsonify, render_template, request
import boto3
import json
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["https://www.videofinding.com"])


def load_output_json(bucket_name):
    s3 = boto3.client('s3')

    try:
        print(f"🔍 S3 버킷 조회 시작: {bucket_name}")
        
        # 모든 폴더 조회 (original/, output/, thumbnails/)
        response = s3.list_objects_v2(Bucket=bucket_name)
        bucket_json = response.get("Contents", [])
        
        print(f"📁 총 파일 개수: {len(bucket_json)}")
        
        # 단순 리스트 형식으로 반환
        key_objects = [obj["Key"] for obj in bucket_json]
        
        # 디버깅을 위한 폴더별 파일 개수 출력
        original_files = [key for key in key_objects if key.startswith('original/')]
        output_files = [key for key in key_objects if key.startswith('output/')]
        thumbnail_files = [key for key in key_objects if key.startswith('thumbnails/')]
        
        print(f"📂 original/ 폴더: {len(original_files)}개 파일")
        print(f"📂 output/ 폴더: {len(output_files)}개 파일")
        print(f"📂 thumbnails/ 폴더: {len(thumbnail_files)}개 파일")
        
        if output_files:
            print(f"🔍 output/ 파일들: {output_files}")
        else:
            print("⚠️ output/ 폴더에 파일이 없습니다!")
            
        # 모든 파일 출력 (디버깅용)
        print("📋 전체 파일 목록:")
        for i, file in enumerate(key_objects):
            print(f"  {i+1}. {file}")
            
        return key_objects  # 리스트 형식으로 반환

    except Exception as e:
        print(f"S3 접근 중 오류: {e}")
        return None


def delete_s3_file(bucket_name, file_key):
    s3 = boto3.client('s3')
    
    try:
        print(f"🗑️ S3 파일 삭제 시작: {bucket_name}/{file_key}")
        
        # 파일 삭제
        response = s3.delete_object(Bucket=bucket_name, Key=file_key)
        
        print(f"✅ 파일 삭제 완료: {file_key}")
        return True
        
    except Exception as e:
        print(f"❌ 파일 삭제 실패: {e}")
        return False


def delete_video_and_related_files(bucket_name, video_path):
    """
    비디오 파일과 관련된 모든 파일들을 삭제합니다.
    - 비디오 파일 자체
    - 관련 썸네일 파일 (실제 존재하는 것만)
    """
    s3 = boto3.client('s3')
    deleted_files = []
    failed_files = []
    
    try:
        print(f"🗑️ 비디오 및 관련 파일 삭제 시작: {video_path}")
        
        # 1. 비디오 파일 자체 삭제
        try:
            s3.delete_object(Bucket=bucket_name, Key=video_path)
            deleted_files.append(video_path)
            print(f"✅ 비디오 파일 삭제 완료: {video_path}")
        except Exception as e:
            failed_files.append(video_path)
            print(f"❌ 비디오 파일 삭제 실패: {video_path} - {e}")
            return {
                "success": False,
                "deleted_files": deleted_files,
                "failed_files": failed_files,
                "error": f"비디오 파일 삭제 실패: {str(e)}"
            }
        
        # 2. 관련 썸네일 파일 찾기 및 삭제
        video_filename = video_path.split('/')[-1]  # 파일명만 추출
        import re
        base_name = re.sub(r'\.[^/.]+$', '', video_filename)  # 확장자 제거
        
        # 비디오 타입에 따른 썸네일 경로 결정 (.jpg만)
        if video_path.startswith('original/'):
            # Original 비디오의 경우
            thumbnail_paths = [
                f"original/thumbnails/{base_name}.jpg"
            ]
        elif video_path.startswith('output/'):
            # Cut 비디오의 경우
            thumbnail_paths = [
                f"thumbnails/{base_name}.jpg"
            ]
        else:
            # 기타 경로의 경우 모든 가능한 경로 확인
            thumbnail_paths = [
                f"thumbnails/{base_name}.jpg",
                f"original/thumbnails/{base_name}.jpg"
            ]
        
        print(f"🔍 찾을 썸네일 파일들: {thumbnail_paths}")
        
        for thumbnail_path in thumbnail_paths:
            try:
                # 파일이 존재하는지 확인
                s3.head_object(Bucket=bucket_name, Key=thumbnail_path)
                
                # 썸네일 파일 삭제
                s3.delete_object(Bucket=bucket_name, Key=thumbnail_path)
                deleted_files.append(thumbnail_path)
                print(f"✅ 썸네일 파일 삭제 완료: {thumbnail_path}")
                
            except s3.exceptions.NoSuchKey:
                # 파일이 존재하지 않으면 무시 (에러로 처리하지 않음)
                print(f"ℹ️ 썸네일 파일이 존재하지 않음: {thumbnail_path}")
                continue
            except Exception as e:
                # 실제 삭제 중 에러가 발생한 경우만 실패로 처리
                failed_files.append(thumbnail_path)
                print(f"❌ 썸네일 파일 삭제 실패: {thumbnail_path} - {e}")
        
        # 비디오 파일이 성공적으로 삭제되었으면 성공으로 처리
        # 썸네일 삭제 실패는 경고로 처리하되, 전체 작업은 성공으로 간주
        success = any(file.endswith('.mp4') for file in deleted_files)
        return {
            "success": success,
            "deleted_files": deleted_files,
            "failed_files": failed_files,
            "message": "비디오 파일 삭제 완료" if success else "비디오 파일 삭제 실패"
        }
        
    except Exception as e:
        print(f"❌ 전체 삭제 프로세스 실패: {e}")
        return {
            "success": False,
            "deleted_files": deleted_files,
            "failed_files": failed_files + [video_path],
            "error": str(e)
        }


# @app.route('/')
# def index():
#     return render_template('index.html')

@app.route('/api/bucket/bucketdata', methods=['GET'])
def get_s3_list():
    BUCKET_NAME = 'video-input-pipeline-20250724'
    result = load_output_json(BUCKET_NAME)
    if result is not None:
        return jsonify(result)  # 리스트 형식으로 JSON 응답
    else:
        return jsonify({"error": "S3 접근 오류"}), 500


@app.route('/api/bucket/deletefile', methods=['DELETE'])
def delete_file():
    BUCKET_NAME = 'video-input-pipeline-20250724'
    
    try:
        data = request.get_json()
        file_key = data.get('file_key')
        
        if not file_key:
            return jsonify({"error": "file_key가 필요합니다"}), 400
        
        print(f"🗑️ 삭제 요청: {file_key}")
        
        # 비디오 파일과 관련 파일들 함께 삭제
        result = delete_video_and_related_files(BUCKET_NAME, file_key)
        
        if result["success"]:
            return jsonify({
                "message": result.get("message", "비디오와 관련 파일들이 성공적으로 삭제되었습니다"),
                "deleted_files": result["deleted_files"],
                "total_deleted": len(result["deleted_files"]),
                "failed_files": result["failed_files"] if result["failed_files"] else []
            })
        else:
            return jsonify({
                "error": result.get("message", "비디오 파일 삭제에 실패했습니다"),
                "deleted_files": result["deleted_files"],
                "failed_files": result["failed_files"]
            }), 500
            
    except Exception as e:
        print(f"❌ 삭제 API 오류: {e}")
        return jsonify({"error": f"서버 오류: {str(e)}"}), 500


# 헬스체크 API
@app.route('/api/bucket/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Bucket list API is running'}), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
