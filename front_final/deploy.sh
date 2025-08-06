#!/bin/bash

# Docker 이미지 빌드
echo "Building Docker image..."
docker build -t my-nextjs-app .

# 기존 컨테이너 중지 및 제거
echo "Stopping and removing existing container..."
docker stop my-nextjs-app || true
docker rm my-nextjs-app || true

# 새 컨테이너 실행
echo "Starting new container..."
docker run -d \
  --name my-nextjs-app \
  -p 3000:3000 \
  --restart unless-stopped \
  my-nextjs-app

echo "Deployment completed!"
echo "Your application is running on http://localhost:3000" 