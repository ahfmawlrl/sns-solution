# SNS 운영 대행 통합 관리 솔루션 — Claude Code 구현 가이드

## 프로젝트 개요

SNS 운영 대행사를 위한 AI 기반 통합 관리 SaaS 플랫폼이다.
클라이언트별 다채널(Instagram, Facebook, YouTube) 콘텐츠 기획→제작→검수→게시→모니터링→분석 전 주기를 자동화한다.

- **제품 형태**: 웹 SaaS (반응형, Desktop 우선)
- **지원 SNS**: Instagram, Facebook, YouTube (Meta Graph API v19, YouTube Data API v3)
- **핵심 차별점**: AI 인사이트 리포트, 자연어 질의 대시보드, RAG 기반 댓글 응대, 브랜드 보이스 학습

---

## 기술 스택

| 계층 | 기술 | 비고 |
|------|------|------|
| Frontend | React 18 + TypeScript, Vite | SPA |
| 상태관리 | Zustand + React Query (TanStack Query v5) | 서버/클라이언트 상태 분리 |
| UI | Tailwind CSS + shadcn/ui (Radix) | 다크모드, WCAG 2.1 AA |
| Backend | FastAPI (Python 3.11) | 비동기, 자동 OpenAPI 문서 |
| ORM | SQLAlchemy 2.0 (async) + Alembic | 마이그레이션 |
| DB | PostgreSQL 16 + pgvector | JSONB, 벡터 검색 |
| Cache/Queue | Redis 7 | 세션, 캐시, Celery Broker, Pub/Sub |
| Task Queue | Celery + Redis Broker | 4단계 우선순위 큐 |
| Storage | AWS S3 / MinIO (dev) | Presigned URL 업로드 |
| Auth | JWT (HS256) + OAuth 2.0 | Access 30분 / Refresh 7일 |
| Realtime | WebSocket (FastAPI) + Redis Pub/Sub | 알림, 위기경보, 댓글 스트림 |
| Container | Docker + Docker Compose | 8개 서비스 |
| Monitoring | Sentry + Prometheus + Grafana | 에러추적, 메트릭, 알람 |
| AI | Claude/GPT-4o, KcELECTRA, pgvector RAG | LLM+ML 하이브리드 |

---

## 프로젝트 디렉토리 구조

```
sns-solution/
├── claude.md                          # ← 이 파일 (메인 구현 가이드)
├── docs/
│   ├── 01-database.md                 # DB 스키마, 인덱스, Redis 구조
│   ├── 02-api-endpoints.md            # 전체 API 엔드포인트 상세
│   ├── 03-frontend-architecture.md    # 라우팅, 상태관리, 컴포넌트
│   ├── 04-auth-security.md            # 인증, RBAC, 보안 정책
│   ├── 05-integrations.md             # SNS API, AI 서비스 연동
│   ├── 06-async-realtime.md           # Celery, WebSocket 설계
│   ├── 07-infra-devops.md             # Docker, CI/CD, 모니터링
│   └── IMPLEMENTATION_ORDER.md        # 구현 순서 (별도 파일)
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 엔트리포인트
│   │   ├── config.py                  # Pydantic Settings
│   │   ├── database.py                # async SQLAlchemy 엔진/세션
│   │   ├── dependencies.py            # DI (get_db, get_current_user, require_role)
│   │   ├── models/                    # SQLAlchemy ORM (14 모델)
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Base, UUID PK mixin, timestamp mixin
│   │   │   ├── user.py
│   │   │   ├── client.py
│   │   │   ├── user_client_assignment.py
│   │   │   ├── platform_account.py
│   │   │   ├── content.py
│   │   │   ├── comment.py
│   │   │   ├── analytics.py
│   │   │   ├── notification.py
│   │   │   ├── audit_log.py
│   │   │   ├── content_approval.py
│   │   │   ├── publishing_log.py
│   │   │   ├── faq_guideline.py
│   │   │   ├── filter_rule.py
│   │   │   └── vector_embedding.py
│   │   ├── schemas/                   # Pydantic V2 request/response
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── client.py
│   │   │   ├── content.py
│   │   │   ├── comment.py
│   │   │   ├── analytics.py
│   │   │   ├── notification.py
│   │   │   ├── publishing.py
│   │   │   ├── ai_tools.py
│   │   │   └── common.py             # PaginatedResponse, ErrorResponse
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── clients.py
│   │   │   │   ├── contents.py
│   │   │   │   ├── publishing.py
│   │   │   │   ├── community.py
│   │   │   │   ├── analytics.py
│   │   │   │   ├── ai_tools.py
│   │   │   │   ├── notifications.py
│   │   │   │   └── settings.py
│   │   │   └── websocket.py
│   │   ├── services/                  # 비즈니스 로직
│   │   │   ├── auth_service.py
│   │   │   ├── user_service.py
│   │   │   ├── client_service.py
│   │   │   ├── content_service.py
│   │   │   ├── publishing_service.py
│   │   │   ├── community_service.py
│   │   │   ├── analytics_service.py
│   │   │   ├── notification_service.py
│   │   │   └── ai_service.py
│   │   ├── repositories/             # Data Access Layer (서비스↔DB 분리)
│   │   │   ├── user_repository.py
│   │   │   ├── client_repository.py
│   │   │   ├── content_repository.py
│   │   │   ├── comment_repository.py
│   │   │   ├── analytics_repository.py
│   │   │   └── notification_repository.py
│   │   ├── integrations/
│   │   │   ├── meta/                 # Instagram + Facebook
│   │   │   │   ├── client.py
│   │   │   │   ├── publisher.py
│   │   │   │   └── insights.py
│   │   │   ├── youtube/
│   │   │   │   ├── client.py
│   │   │   │   ├── publisher.py
│   │   │   │   └── insights.py
│   │   │   └── ai/
│   │   │       ├── llm_client.py     # Claude/GPT 통합 클라이언트
│   │   │       ├── sentiment.py      # 감성 분석
│   │   │       ├── rag.py            # RAG 파이프라인
│   │   │       └── embeddings.py     # 벡터 임베딩 생성
│   │   ├── tasks/                    # Celery 작업
│   │   │   ├── celery_app.py
│   │   │   ├── publishing_tasks.py
│   │   │   ├── ai_tasks.py
│   │   │   ├── data_collection_tasks.py
│   │   │   └── report_tasks.py
│   │   ├── middleware/
│   │   │   ├── cors.py
│   │   │   ├── error_handler.py
│   │   │   ├── logging_middleware.py
│   │   │   └── rate_limiter.py
│   │   └── utils/
│   │       ├── encryption.py         # AES-256-GCM 토큰 암호화
│   │       ├── file_validation.py    # MIME 타입, 크기 검증
│   │       └── helpers.py
│   ├── alembic/
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_contents.py
│   │   └── ...
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── App.tsx
│   │   │   ├── Router.tsx
│   │   │   ├── providers.tsx          # QueryClient, Zustand, Theme
│   │   │   └── main.tsx
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui 컴포넌트
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── MainLayout.tsx
│   │   │   │   └── ClientSwitcher.tsx
│   │   │   ├── feedback/
│   │   │   │   ├── Toast.tsx
│   │   │   │   ├── ErrorBoundary.tsx
│   │   │   │   └── LoadingSpinner.tsx
│   │   │   ├── charts/
│   │   │   └── common/
│   │   │       ├── EmptyState.tsx
│   │   │       ├── Skeleton.tsx
│   │   │       └── Pagination.tsx
│   │   ├── features/
│   │   │   ├── dashboard/
│   │   │   ├── content/
│   │   │   │   ├── ContentCalendar.tsx
│   │   │   │   ├── KanbanBoard.tsx
│   │   │   │   ├── ContentEditor.tsx
│   │   │   │   ├── ContentDetail.tsx
│   │   │   │   └── PlatformPreview.tsx
│   │   │   ├── publishing/
│   │   │   ├── community/
│   │   │   │   ├── UnifiedInbox.tsx
│   │   │   │   └── SentimentDashboard.tsx
│   │   │   ├── analytics/
│   │   │   │   └── AnalyticsDashboard.tsx
│   │   │   ├── clients/
│   │   │   ├── ai-tools/
│   │   │   │   └── AIChatPanel.tsx
│   │   │   ├── notifications/
│   │   │   │   └── NotificationCenter.tsx
│   │   │   └── settings/
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useWebSocket.ts
│   │   │   └── useDebounce.ts
│   │   ├── stores/
│   │   │   ├── authStore.ts
│   │   │   ├── clientStore.ts
│   │   │   ├── uiStore.ts
│   │   │   ├── chatStore.ts
│   │   │   └── notificationStore.ts
│   │   ├── api/
│   │   │   ├── client.ts              # Axios 인스턴스 + interceptors
│   │   │   ├── auth.ts
│   │   │   ├── users.ts
│   │   │   ├── clients.ts
│   │   │   ├── contents.ts
│   │   │   ├── publishing.ts
│   │   │   ├── community.ts
│   │   │   ├── analytics.ts
│   │   │   ├── ai.ts
│   │   │   ├── notifications.ts
│   │   │   └── settings.ts
│   │   ├── types/
│   │   │   └── index.ts               # 전체 TypeScript 타입 정의
│   │   └── utils/
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── nginx/
│   └── nginx.conf
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
└── README.md
```

---

## 사용자 역할 (RBAC 4종)

| 역할 | 코드 | 설명 |
|------|------|------|
| **admin** | `admin` | 시스템 전체 관리, 사용자 관리, 모든 권한 |
| **manager** | `manager` | 클라이언트 총괄, 콘텐츠 승인, 워크플로우 설정 |
| **operator** | `operator` | 콘텐츠 기획/제작, 댓글 관리, 게시 실행 |
| **client** | `client` | 본인 계정 성과 조회, 콘텐츠 승인, AI 질의 |

RBAC는 FastAPI Dependency로 구현: `require_role("admin", "manager")` 형태의 DI 데코레이터.

---

## 핵심 비즈니스 플로우

```
콘텐츠 기획 → 제작(AI 지원) → 품질검증(AI) → 내부검토 → 클라이언트승인
→ 플랫폼별 변환 → 다중채널 게시(예약/즉시) → 커뮤니티 모니터링(AI 감성분석)
→ 성과 수집 → AI 인사이트 리포트 → 전략 추천
```

콘텐츠 상태 흐름: `draft → review → client_review → approved → published` (rejected에서 draft로 복귀 가능)

---

## 구현 시 핵심 원칙

1. **API 응답 표준화**: 모든 응답은 `{ status: "success"|"error", data, message, pagination? }` 형태
2. **오류 포맷**: RFC 7807 Problem Details
3. **페이지네이션**: cursor 기반 (무한스크롤) + offset 기반 (페이지) 복합 지원
4. **인증**: 모든 API에 Bearer Token 필수 (auth 엔드포인트 제외)
5. **감사 로그**: 모든 CUD + 승인/게시 작업에 audit_logs 자동 기록
6. **환경 분리**: .env 기반 Pydantic Settings, 절대 하드코딩 금지

---

## 부속 문서 참조 안내

상세 스펙은 `docs/` 디렉토리의 각 문서를 참조한다:

| 파일 | 내용 | 구현 시점 |
|------|------|-----------|
| `docs/01-database.md` | DB 14개 테이블 스키마, 인덱스 14종, Redis 10종 키 구조 | Phase 1 시작 |
| `docs/02-api-endpoints.md` | 10개 도메인 72개 API 엔드포인트 전체 명세 | Phase 1~2 |
| `docs/03-frontend-architecture.md` | 라우팅 12개, Zustand 5개 Store, 컴포넌트 9종, 에러/반응형/접근성 | Phase 1~2 |
| `docs/04-auth-security.md` | JWT 이중 토큰, RBAC 매트릭스, 보안 8항목, 파일 업로드 정책 | Phase 1 시작 |
| `docs/05-integrations.md` | Meta/YouTube API, AI 5종 연동, Circuit Breaker/Retry 전략 | Phase 1~2 |
| `docs/06-async-realtime.md` | Celery 5종 작업 유형, WebSocket 6종 이벤트 | Phase 1~2 |
| `docs/07-infra-devops.md` | Docker Compose 8서비스, 환경변수, 백업, 모니터링, CI/CD | Phase 1 시작 |
| `docs/IMPLEMENTATION_ORDER.md` | **전체 구현 순서 (31 단계)** | 항상 참조 |

---

## 빠른 시작 (개발 환경 세팅)

```bash
# 1. 저장소 클론
git clone <repo-url> sns-solution && cd sns-solution

# 2. 환경 변수 설정
cp .env.example .env   # 필수 변수 편집

# 3. Docker Compose 실행 (infra only)
docker compose up -d postgres redis minio

# 4. Backend 세팅
cd backend
poetry install
alembic upgrade head          # DB 마이그레이션
poetry run uvicorn app.main:app --reload --port 8000

# 5. Frontend 세팅
cd ../frontend
pnpm install
pnpm dev                      # Vite dev server (port 3000)

# 6. Celery Worker
cd ../backend
celery -A app.tasks.celery_app worker --loglevel=info -Q critical,high,medium,low
celery -A app.tasks.celery_app beat --loglevel=info
```

---

## 코드 품질 기준

- **Backend**: Ruff (lint+format), mypy (strict), pytest ≥80% coverage
- **Frontend**: ESLint + Prettier, TypeScript strict, Vitest + React Testing Library
- **API 문서**: FastAPI 자동 생성 → `/docs` (Swagger), `/redoc`
- **Git**: Conventional Commits, PR 리뷰 필수, `main` / `develop` / `feature/*` 브랜치
- **DB 변경**: 반드시 Alembic 마이그레이션, downgrade 필수 작성
