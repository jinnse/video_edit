# 빠른 배포 가이드

## 로컬에서 테스트

```bash
# 1. Docker 이미지 빌드
docker build -t my-nextjs-app .

# 2. 컨테이너 실행
docker run -d --name my-nextjs-app -p 3000:3000 my-nextjs-app

# 3. 접속 확인
# 브라우저에서 http://localhost:3000 접속
```

## EC2 배포

```bash
# 1. EC2에 Docker 설치
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# 2. 프로젝트 파일 업로드
scp -r ./* ec2-user@YOUR-EC2-IP:/home/ec2-user/app/

# 3. EC2에 접속
ssh ec2-user@YOUR-EC2-IP

# 4. 배포 실행
cd /home/ec2-user/app
chmod +x deploy.sh
./deploy.sh

# 5. 접속 확인
# 브라우저에서 http://YOUR-EC2-IP:3000 접속
```

## Docker Compose 사용

```bash
# 1. Docker Compose 설치 (EC2에서)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 2. 배포
docker-compose up -d --build

# 3. 로그 확인
docker-compose logs -f
```

## 유용한 명령어

```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인
docker logs my-nextjs-app

# 컨테이너 재시작
docker restart my-nextjs-app

# 컨테이너 중지
docker stop my-nextjs-app

# 컨테이너 제거
docker rm my-nextjs-app
``` 