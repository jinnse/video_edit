const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// 미들웨어
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// 기본 라우트
app.get('/', (req, res) => {
  res.json({
    message: '🚀 Node.js API 서버가 실행 중입니다!',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development',
    version: '1.0.0'
  });
});

// 헬스 체크
app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    uptime: process.uptime(),
    timestamp: new Date().toISOString()
  });
});

// API 라우트
app.get('/api/users', (req, res) => {
  res.json({
    users: [
      { id: 1, name: '사용자1', email: 'user1@example.com' },
      { id: 2, name: '사용자2', email: 'user2@example.com' }
    ]
  });
});

app.post('/api/users', (req, res) => {
  const { name, email } = req.body;
  res.json({
    message: '사용자가 생성되었습니다',
    user: { id: Date.now(), name, email }
  });
});

// 데이터베이스 연결 테스트 (PostgreSQL)
app.get('/api/db-test', async (req, res) => {
  try {
    // 실제 환경에서는 데이터베이스 연결 코드 추가
    res.json({
      message: '데이터베이스 연결 테스트',
      status: 'PostgreSQL 연결 준비됨'
    });
  } catch (error) {
    res.status(500).json({
      message: '데이터베이스 연결 실패',
      error: error.message
    });
  }
});

// Redis 연결 테스트
app.get('/api/cache-test', async (req, res) => {
  try {
    // 실제 환경에서는 Redis 연결 코드 추가
    res.json({
      message: 'Redis 캐시 테스트',
      status: 'Redis 연결 준비됨'
    });
  } catch (error) {
    res.status(500).json({
      message: 'Redis 연결 실패',
      error: error.message
    });
  }
});

// 404 핸들러
app.use('*', (req, res) => {
  res.status(404).json({
    message: '요청한 리소스를 찾을 수 없습니다',
    path: req.originalUrl
  });
});

// 에러 핸들러
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    message: '서버 내부 오류가 발생했습니다',
    error: process.env.NODE_ENV === 'development' ? err.message : {}
  });
});

// 서버 시작
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 서버가 포트 ${PORT}에서 실행 중입니다`);
  console.log(`환경: ${process.env.NODE_ENV || 'development'}`);
  console.log(`시작 시간: ${new Date().toISOString()}`);
});
