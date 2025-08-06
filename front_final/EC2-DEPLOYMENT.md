# EC2 Docker 배포 가이드

## 1. EC2 인스턴스 준비

### 1.1 보안 그룹 설정
- 인바운드 규칙에 포트 3000 추가 (HTTP)
- 소스: 0.0.0.0/0 (모든 IP 허용) 또는 특정 IP

### 1.2 EC2에 Docker 설치
```bash
# 시스템 업데이트
sudo yum update -y

# Docker 설치
sudo yum install -y docker

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자를 docker 그룹에 추가
sudo usermod -a -G docker ec2-user

# 새로운 그룹 권한 적용을 위해 재로그인
exit
# 다시 SSH로 접속
```

## 2. 애플리케이션 배포

### 2.1 프로젝트 파일 업로드
```bash
# 프로젝트 파일들을 EC2로 업로드
scp -r ./* ec2-user@your-ec2-ip:/home/ec2-user/app/
```

### 2.2 Docker 이미지 빌드 및 실행
```bash
# EC2에 접속
ssh ec2-user@your-ec2-ip

# 프로젝트 디렉토리로 이동
cd /home/ec2-user/app

# Docker 이미지 빌드
docker build -t my-nextjs-app .

# 컨테이너 실행
docker run -d \
  --name my-nextjs-app \
  -p 3000:3000 \
  --restart unless-stopped \
  my-nextjs-app
```

## 3. 배포 스크립트 사용

### 3.1 스크립트 권한 설정
```bash
chmod +x deploy.sh
```

### 3.2 배포 실행
```bash
./deploy.sh
```

## 4. Docker Compose 사용 (권장)

### 4.1 Docker Compose 설치
```bash
# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 4.2 Compose로 배포
```bash
# 컨테이너 빌드 및 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 컨테이너 중지
docker-compose down
```

## 5. 접속 확인

### 5.1 로컬에서 접속 테스트
```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인
docker logs my-nextjs-app
```

### 5.2 웹 브라우저에서 접속
- EC2 공인 IP:3000 으로 접속
- 예: http://your-ec2-public-ip:3000

## 6. 유지보수 명령어

### 6.1 컨테이너 관리
```bash
# 컨테이너 상태 확인
docker ps -a

# 컨테이너 중지
docker stop my-nextjs-app

# 컨테이너 시작
docker start my-nextjs-app

# 컨테이너 재시작
docker restart my-nextjs-app

# 컨테이너 제거
docker rm my-nextjs-app
```

### 6.2 이미지 관리
```bash
# 이미지 목록 확인
docker images

# 이미지 제거
docker rmi my-nextjs-app
```

### 6.3 로그 확인
```bash
# 실시간 로그 확인
docker logs -f my-nextjs-app

# 최근 로그 확인
docker logs --tail 100 my-nextjs-app
```

## 7. 문제 해결

### 7.1 포트 충돌
```bash
# 포트 사용 확인
sudo netstat -tulpn | grep :3000

# 다른 포트로 실행
docker run -d --name my-nextjs-app -p 8080:3000 my-nextjs-app
```

### 7.2 권한 문제
```bash
# Docker 그룹 확인
groups

# Docker 서비스 재시작
sudo systemctl restart docker
```

### 7.3 디스크 공간 부족
```bash
# 사용하지 않는 Docker 리소스 정리
docker system prune -a
```

## 8. 자동 배포 설정 (선택사항)

### 8.1 systemd 서비스 등록
```bash
# 서비스 파일 생성
sudo tee /etc/systemd/system/docker-app.service << EOF
[Unit]
Description=My Next.js App
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ec2-user/app
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl enable docker-app.service
sudo systemctl start docker-app.service
```

이제 EC2에서 Docker 컨테이너로 웹사이트를 배포할 수 있습니다! 