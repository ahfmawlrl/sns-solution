# SNS 운영 대행 통합 관리 솔루션

SNS 운영 대행사를 위한 AI 기반 통합 관리 SaaS 플랫폼.
클라이언트별 다채널(Instagram, Facebook, YouTube) 콘텐츠 기획-제작-검수-게시-모니터링-분석 전 주기를 자동화한다.

## 기술 스택

| 계층 | 기술 |
|------|------|
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS, shadcn/ui |
| 상태관리 | Zustand + TanStack Query v5 |
| Backend | FastAPI (Python 3.11), SQLAlchemy 2.0 async |
| DB | PostgreSQL 16 + pgvector |
| Cache/Queue | Redis 7, Celery |
| Storage | AWS S3 / MinIO |
| Auth | JWT (HS256) + OAuth 2.0 |
| Realtime | WebSocket + Redis Pub/Sub |
| AI | Claude/GPT-4o, 감성분석, RAG (pgvector) |
| Infra | Docker Compose, Nginx, Prometheus, Grafana, Sentry |

## 빠른 시작

### 방법 A: Docker Compose (전체 스택)

```bash
cp .env.example .env        # 환경 변수 편집
docker compose up -d         # 전체 서비스 기동 (10개)
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- MinIO Console: http://localhost:9001
- Grafana: http://localhost:3001

### 방법 B: 로컬 개발 (인프라만 Docker)

```bash
# 1. 인프라
docker compose up -d postgres redis minio minio-init

# 2. 백엔드
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
# python -m venv .venv && source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt                   # 또는: poetry install
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. 프론트엔드 (별도 터미널)
cd frontend
pnpm install
pnpm dev

# 4. Celery Worker (별도 터미널)
cd backend
celery -A app.tasks.celery_app worker --loglevel=info -Q critical,high,medium,low

# 5. Celery Beat (별도 터미널)
cd backend
celery -A app.tasks.celery_app beat --loglevel=info
```

## 프로젝트 구조

```
sns-solution/
├── backend/                   # FastAPI 백엔드
│   ├── app/
│   │   ├── api/v1/            # API 엔드포인트 (10개 도메인)
│   │   ├── models/            # SQLAlchemy ORM (14 모델)
│   │   ├── schemas/           # Pydantic V2 스키마
│   │   ├── services/          # 비즈니스 로직
│   │   ├── repositories/      # 데이터 접근 계층
│   │   ├── integrations/      # Meta, YouTube, AI 연동
│   │   ├── tasks/             # Celery 비동기 작업
│   │   ├── middleware/        # CORS, Rate Limit, 감사 로그
│   │   └── utils/             # 암호화, 파일 검증, 헬퍼
│   ├── alembic/               # DB 마이그레이션
│   ├── tests/                 # pytest 테스트 (318 tests)
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                  # React SPA
│   ├── src/
│   │   ├── app/               # 라우터, 프로바이더, 엔트리
│   │   ├── components/        # UI(shadcn), 레이아웃, 피드백, 공통
│   │   ├── features/          # 대시보드, 콘텐츠, 커뮤니티, 분석, AI
│   │   ├── stores/            # Zustand (auth, client, ui, chat, notification)
│   │   ├── hooks/             # useAuth, useWebSocket, useDebounce
│   │   ├── api/               # Axios API 클라이언트 (10개 모듈)
│   │   └── types/             # TypeScript 타입 정의
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml         # 개발 환경 (10 서비스)
├── docker-compose.prod.yml    # 프로덕션 환경
├── nginx/nginx.conf
├── monitoring/                # Prometheus, Grafana 설정
├── docs/                      # 상세 설계 문서 (7종 + 구현 순서)
└── .env.example
```

## 환경 변수

`.env.example`을 복사하여 `.env`를 생성하고 값을 설정한다.

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 접속 URL | `postgresql+asyncpg://postgres:postgres@localhost:5432/sns_solution` |
| `REDIS_URL` | Redis 접속 URL | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | JWT 서명 키 | (반드시 변경) |
| `AI_PROVIDER` | AI 프로바이더 (claude/openai) | `claude` |
| `ANTHROPIC_API_KEY` | Claude API 키 | |
| `OPENAI_API_KEY` | OpenAI API 키 | |
| `S3_ENDPOINT` | S3/MinIO 엔드포인트 | `http://localhost:9000` |

전체 목록은 `.env.example` 참조.

## 테스트

```bash
# 백엔드
cd backend
pytest --tb=short -q              # 318 tests

# 프론트엔드
cd frontend
pnpm test                         # 68 tests
pnpm type-check                   # TypeScript 검사
```

## 사용자 역할 (RBAC)

| 역할 | 설명 |
|------|------|
| `admin` | 시스템 전체 관리, 사용자 관리 |
| `manager` | 클라이언트 총괄, 콘텐츠 승인 |
| `operator` | 콘텐츠 기획/제작, 댓글 관리 |
| `client` | 본인 계정 조회, 콘텐츠 승인 |

## API 문서

백엔드 기동 후 자동 생성:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 라이선스

Private - All rights reserved.
