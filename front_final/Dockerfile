# 멀티스테이지 빌드를 사용하여 최적화된 이미지 생성
FROM node:20-alpine AS base

# 의존성 설치를 위한 단계
FROM base AS deps
WORKDIR /app

# package.json 복사
COPY package.json ./
RUN npm install --only=production --legacy-peer-deps

# 빌드 단계
FROM base AS builder
WORKDIR /app
COPY package.json ./
RUN npm install --legacy-peer-deps
COPY . .

# Next.js 빌드
RUN npm run build

# 프로덕션 이미지
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production

# 시스템 사용자 생성 (보안상 권장)
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 빌드된 애플리케이션 복사
COPY --from=builder /app/public ./public

# Next.js 빌드 결과물 복사
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# 포트 노출
EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# 애플리케이션 실행
CMD ["node", "server.js"] 
