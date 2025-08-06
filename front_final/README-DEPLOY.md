# 🚀 Docker 배포 가이드

## 📋 사전 요구사항

- Docker 설치
- Docker Compose 설치
- EC2 인스턴스 (Ubuntu 20.04+ 권장)

## 🔧 EC2 설정

### 1. Docker 설치
```bash
# Docker 설치
sudo apt update
sudo apt install -y docker.io docker-compose

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
```

### 2. 보안 그룹 설정
- **인바운드 규칙**: 포트 3000 열기
- **소스**: 0.0.0.0/0 (또는 특정 IP)

## 🐳 배포 방법

### 방법 1: Docker Compose 사용 (권장)
```bash
# 프로젝트 디렉토리로 이동
cd video_edit-issue-23-frontend-files/front_web

# 배포 스크립트 실행 권한 부여
chmod +x deploy.sh

# 배포 실행
./deploy.sh
```

### 방법 2: 수동 배포
```bash
# 이미지 빌드
docker-compose build

# 컨테이너 실행
docker-compose up -d

# 상태 확인
docker-compose ps
```

## 🌐 접속 방법

배포 완료 후 다음 주소로 접속:
```
http://your-ec2-public-ip:3000
```

## 📊 관리 명령어

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f

# 컨테이너 중지
docker-compose down

# 컨테이너 재시작
docker-compose restart

# 이미지 업데이트
docker-compose pull
docker-compose up -d
```

## 🔍 문제 해결

### 포트가 열려있지 않은 경우
```bash
# 방화벽 설정
sudo ufw allow 3000
sudo ufw enable
```

### 컨테이너가 시작되지 않는 경우
```bash
# 로그 확인
docker-compose logs

# 컨테이너 재빌드
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 📝 환경 변수 설정

필요한 경우 `.env` 파일 생성:
```bash
# .env 파일 생성
cat > .env << EOF
NODE_ENV=production
PORT=3000
EOF
```

## 🎯 성능 최적화

### nginx 리버스 프록시 설정 (선택사항)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## ✅ 배포 확인 체크리스트

- [ ] Docker 설치 완료
- [ ] 보안 그룹 포트 3000 열기
- [ ] 이미지 빌드 성공
- [ ] 컨테이너 실행 확인
- [ ] 웹사이트 접속 확인
- [ ] API 연결 확인 (필요시)

## 🆘 지원

문제가 발생하면 다음을 확인하세요:
1. Docker 서비스 상태: `sudo systemctl status docker`
2. 컨테이너 로그: `docker-compose logs`
3. 포트 사용 상태: `sudo netstat -tlnp | grep 3000` 