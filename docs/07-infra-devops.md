# 07. 인프라 및 DevOps

## 1. Docker Compose 구성 (8 서비스)

| 서비스 | 포트 | 이미지 | 설명 |
|--------|------|--------|------|
| frontend | 3000 | node:20-alpine | Vite Dev (개발) / Nginx (프로덕션) |
| backend | 8000 | python:3.12-slim | FastAPI + Uvicorn (4 workers) |
| postgres | 5432 | postgres:16-alpine | PostgreSQL + pgvector 확장 |
| redis | 6379 | redis:7-alpine | Cache + Broker + Pub/Sub |
| celery-worker | - | backend 기반 | Celery Worker (concurrency=4) |
| celery-beat | - | backend 기반 | Celery Beat 스케줄러 |
| nginx | 80/443 | nginx:alpine | Reverse Proxy + SSL + 정적 파일 |
| minio | 9000/9001 | minio/minio | S3 호환 파일 저장소 (개발용) |

```yaml
# docker-compose.yml
version: "3.9"
services:
  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: sns_solution
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
    environment:
      MINIO_ROOT_USER: ${S3_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY:-minioadmin}
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --workers 1
    volumes:
      - ./backend:/app

  celery-worker:
    build: ./backend
    env_file: .env
    depends_on: [backend]
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4 -Q critical,high,medium,low

  celery-beat:
    build: ./backend
    env_file: .env
    depends_on: [backend]
    command: celery -A app.tasks.celery_app beat --loglevel=info

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: pnpm dev --host

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    depends_on: [backend, frontend]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### Nginx 설정

```nginx
# nginx/nginx.conf
upstream backend {
    server backend:8000;
}
upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name _;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;

    # Frontend SPA
    location / {
        proxy_pass http://frontend;
    }

    # API 프록시
    location /api/ {
        limit_req zone=api burst=20;
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket 프록시
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # 정적 파일 (프로덕션)
    location /static/ {
        alias /var/www/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 2. 환경 변수 관리

`.env.example` — 모든 필수 환경 변수 목록:

```bash
# ── Database ──
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sns_solution

# ── Redis ──
REDIS_URL=redis://localhost:6379/0

# ── JWT ──
JWT_SECRET_KEY=your-256bit-secret-key-here  # openssl rand -hex 32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Meta (Instagram/Facebook) ──
META_APP_ID=
META_APP_SECRET=

# ── YouTube ──
YOUTUBE_API_KEY=
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=

# ── AI ──
AI_PROVIDER=claude              # claude | openai
ANTHROPIC_API_KEY=              # Claude API Key
OPENAI_API_KEY=                 # GPT-4o / Embedding API Key
EMBEDDING_MODEL=text-embedding-3-small  # OpenAI 임베딩 모델

# ── S3 / MinIO ──
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=sns-media
S3_REGION=ap-northeast-2

# ── Encryption ──
ENCRYPTION_KEY=your-32byte-aes-key  # openssl rand -hex 32

# ── Sentry ──
SENTRY_DSN=

# ── CORS ──
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# ── WebSocket ──
WS_MAX_CONNECTIONS=1000

# ── App ──
APP_ENV=development             # development | staging | production
LOG_LEVEL=DEBUG                 # DEBUG | INFO | WARNING | ERROR
```

```python
# app/config.py — Pydantic Settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    YOUTUBE_API_KEY: str = ""
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_PROVIDER: str = "claude"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET_NAME: str = "sns-media"
    ENCRYPTION_KEY: str = ""
    SENTRY_DSN: str = ""
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"
    WS_MAX_CONNECTIONS: int = 1000
    APP_ENV: str = "development"
    LOG_LEVEL: str = "DEBUG"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 3. 백업 및 복구 전략

**목표**: RPO 1시간 / RTO 4시간

| 대상 | 주기 | 방식 | 보관 기간 |
|------|------|------|---------|
| PostgreSQL 전체 | 일 1회 (새벽 3시) | `pg_dump` → S3 | 30일 |
| PostgreSQL WAL | 실시간 | WAL 아카이빙, PITR 지원 | 7일 |
| Redis | 1시간 | RDB 스냅샷 → S3 | 7일 |
| S3/MinIO 미디어 | 실시간 | 버전관리 + Cross-Region 복제 (프로덕션) | 무기한 |
| 설정 파일 | 변경 시 | Git 버전 관리 | 무기한 |

```bash
# 백업 스크립트 예시 (Cron 등록)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M)
pg_dump $DATABASE_URL | gzip > /backups/db_${DATE}.sql.gz
aws s3 cp /backups/db_${DATE}.sql.gz s3://sns-backups/postgres/
find /backups -name "db_*.sql.gz" -mtime +30 -delete
```

복구 Runbook: `/docs/runbook/` 디렉토리에 문서화

---

## 4. 모니터링 스택

### 구성

| 도구 | 역할 |
|------|------|
| **Sentry** | Backend + Frontend 에러 추적, 소스맵 연동 |
| **Prometheus** | 메트릭 수집 (API 응답시간, DB 커넥션, Celery 큐) |
| **Grafana** | 대시보드 시각화, Alerting → Slack/이메일 |
| **structlog** | JSON 포맷 구조화 로깅 → stdout → Docker 로그 수집 |

### 로그 레벨 전략

| 환경 | 레벨 |
|------|------|
| 개발 (development) | DEBUG |
| 스테이징 (staging) | INFO |
| 프로덕션 (production) | WARNING + ERROR |

```python
# Sentry 초기화
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1 if settings.APP_ENV == "production" else 1.0,
        environment=settings.APP_ENV,
    )
```

### 핵심 모니터링 지표 (8종)

| 지표 | 임계치 | 알람 조건 |
|------|--------|---------|
| API 응답시간 P95 | < 500ms | P95 > 800ms 지속 5분 → Slack |
| Celery 대기열 길이 | < 100 | 200 초과 → 알림 |
| PostgreSQL 슬로우 쿼리 | < 100ms | 100ms 초과 자동 로깅 |
| Redis 메모리 사용량 | < 80% | 80% 초과 → 알림 |
| SNS API 성공률 | > 99% | 95% 미만 → 알림 |
| WebSocket 동시 연결 | < 1000 | 800 초과 → 경고 |
| 디스크 사용량 (PG) | < 80% | 80% 초과 → 긴급 |
| Celery Worker 상태 | 전체 active | Worker 다운 → 즉시 |

---

## 5. CI/CD 파이프라인 (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI
on:
  pull_request:
    branches: [develop, main]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env: { POSTGRES_DB: test, POSTGRES_PASSWORD: test }
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install poetry && cd backend && poetry install
      - run: cd backend && poetry run ruff check .          # Lint
      - run: cd backend && poetry run mypy app/              # Type check
      - run: cd backend && poetry run pytest --cov=app --cov-report=xml  # Test

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm, cache-dependency-path: frontend/pnpm-lock.yaml }
      - run: cd frontend && pnpm install
      - run: cd frontend && pnpm lint                        # ESLint
      - run: cd frontend && pnpm type-check                  # TypeScript
      - run: cd frontend && pnpm test                        # Vitest
```

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
  workflow_dispatch:         # 수동 트리거

jobs:
  deploy-staging:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker-compose.prod.yml build
      - run: docker compose -f docker-compose.prod.yml push
      # 스테이징 자동 배포
      - run: ssh staging "cd /app && docker compose pull && docker compose up -d"

  deploy-production:
    if: startsWith(github.ref, 'refs/tags/v')
    needs: deploy-staging
    environment: production       # 승인 필요
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker-compose.prod.yml build
      - run: docker compose -f docker-compose.prod.yml push
      - run: ssh production "cd /app && docker compose pull && docker compose up -d"
```

### 배포 전략

| 환경 | 트리거 | 승인 |
|------|--------|------|
| 스테이징 | `main` 병합 시 자동 | 불필요 |
| 프로덕션 | `v*` 태그 시 수동 | GitHub Environment 승인 필수 |

---

## 6. 개발 환경 요구사항

| 도구 | 버전 |
|------|------|
| Node.js | 20 LTS |
| pnpm | 9+ |
| Python | 3.12+ |
| Poetry | 1.8+ |
| Docker | 24+ (Docker Desktop 또는 OrbStack) |

### VS Code 추천 확장

- Ruff (Python lint/format)
- ESLint + Prettier
- Tailwind CSS IntelliSense
- Python (Microsoft)
- Docker
- GitLens
