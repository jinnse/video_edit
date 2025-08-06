#!/bin/bash

# EC2 배포 스크립트
# 사용법: ./deploy-ec2.sh

set -e

# 변수 설정
EC2_IP="54.181.2.149"
KEY_PATH="$HOME/video-edit-keypair.pem"
PROJECT_DIR="/mnt/c/Users/DSO/video_edit"
REMOTE_DIR="/home/ec2-user/video-edit"

echo "🚀 EC2 인스턴스에 Video Edit 애플리케이션 배포 시작..."

# 1. 프로젝트 파일을 EC2로 복사
echo "📁 프로젝트 파일 복사 중..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ec2-user@$EC2_IP "mkdir -p $REMOTE_DIR"

# 필요한 파일들만 복사
scp -i "$KEY_PATH" -r "$PROJECT_DIR/app.py" ec2-user@$EC2_IP:$REMOTE_DIR/
scp -i "$KEY_PATH" -r "$PROJECT_DIR/templates" ec2-user@$EC2_IP:$REMOTE_DIR/
scp -i "$KEY_PATH" -r "$PROJECT_DIR/requirements.txt" ec2-user@$EC2_IP:$REMOTE_DIR/
scp -i "$KEY_PATH" -r "$PROJECT_DIR/api" ec2-user@$EC2_IP:$REMOTE_DIR/

# 2. EC2에서 환경 설정 및 애플리케이션 실행
echo "⚙️ EC2에서 환경 설정 중..."
ssh -i "$KEY_PATH" ec2-user@$EC2_IP << 'EOF'
    # 시스템 업데이트
    sudo yum update -y
    
    # Python 3 및 pip 설치
    sudo yum install -y python3 python3-pip
    
    # 프로젝트 디렉토리로 이동
    cd /home/ec2-user/video-edit
    
    # Python 가상환경 생성
    python3 -m venv venv
    source venv/bin/activate
    
    # 의존성 설치
    pip install -r requirements.txt
    
    # 기존 프로세스 종료 (있다면)
    pkill -f "python.*app.py" || true
    
    # 애플리케이션 백그라운드 실행
    nohup python3 app.py > app.log 2>&1 &
    
    echo "✅ 애플리케이션이 포트 5000에서 실행 중입니다"
    echo "🌐 웹사이트 주소: http://54.181.2.149:5000"
EOF

echo ""
echo "🎉 배포 완료!"
echo "🌐 웹사이트: http://$EC2_IP:5000"
echo "📊 상태 확인: http://$EC2_IP:5000/health"
echo ""
echo "📝 로그 확인 방법:"
echo "   ssh -i $KEY_PATH ec2-user@$EC2_IP"
echo "   cd /home/ec2-user/video-edit"
echo "   tail -f app.log"
