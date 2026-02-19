# 구현 순서서 (Implementation Order)

> **원칙**: 의존성 순서대로 진행. 각 단계의 검증 기준을 통과해야 다음 단계 진행.
> **참조 문서**: 각 단계에서 참조할 docs/ 파일을 명시.

---

## Phase 0: 프로젝트 초기화 (1일)

### STEP 01. 프로젝트 스캐폴딩
```
참조: claude.md (디렉토리 구조), docs/07-infra-devops.md
```

**작업 내용**:
- 모노레포 루트 디렉토리 생성 (`sns-solution/`)
- `backend/`: Poetry 프로젝트 초기화 (`pyproject.toml`)
  - 의존성: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, redis, celery, pydantic-settings, python-jose[cryptography], passlib[bcrypt], httpx, python-magic, sentry-sdk, structlog
- `frontend/`: Vite + React + TypeScript 프로젝트 초기화 (`pnpm create vite`)
  - 의존성: react-router-dom, zustand, @tanstack/react-query, axios, tailwindcss, @radix-ui, recharts, @dnd-kit/core, tiptap, react-dropzone, date-fns, zod, react-hook-form
- `.env.example` 생성 (전체 환경 변수 목록)
- `.gitignore`, `README.md` 생성
- Git 초기화 + 첫 커밋

**검증**: `poetry install` / `pnpm install` 에러 없이 완료, `docker compose config` 유효

---

### STEP 02. Docker Compose 인프라
```
참조: docs/07-infra-devops.md (Section 1)
```

**작업 내용**:
- `docker-compose.yml` 작성 (postgres, redis, minio 3개 서비스 우선)
- PostgreSQL: pgvector 확장 이미지 사용 (`pgvector/pgvector:pg16`)
- MinIO: 버킷 자동 생성 초기화 스크립트
- `nginx/nginx.conf` 기본 설정

**검증**: `docker compose up -d postgres redis minio` 후 각 서비스 헬스체크 통과

---

## Phase 1: 백엔드 코어 (5일)

### STEP 03. FastAPI 기본 설정 + DB 연결
```
참조: docs/07-infra-devops.md (Section 2), claude.md (구현 원칙)
```

**작업 내용**:
- `app/config.py`: Pydantic Settings (전체 환경 변수)
- `app/database.py`: async SQLAlchemy 엔진 + 세션 팩토리
- `app/main.py`: FastAPI 앱 + lifespan (DB 연결/해제)
- `app/middleware/`: CORS, 에러 핸들러, 로깅 미들웨어
- 헬스체크 엔드포인트: `GET /health`

**검증**: `uvicorn app.main:app --reload` 기동, `/health` 200 응답, `/docs` Swagger UI 접근

---

### STEP 04. ORM 모델 정의 (14 테이블)
```
참조: docs/01-database.md (전체)
```

**작업 내용**:
- `app/models/base.py`: Base, UUIDMixin, TimestampMixin
- 핵심 6종: user, client, platform_account, content, comment, analytics
- 연결 2종: user_client_assignment, filter_rule
- 추가 6종: notification, audit_log, content_approval, publishing_log, faq_guideline, vector_embedding
- ENUM 타입 정의 (UserRole, ContentStatus, Sentiment, etc.)
- 테이블 간 관계 설정 (FK, relationship)

**검증**: `alembic revision --autogenerate` → 마이그레이션 파일 생성 → `alembic upgrade head` 성공

**의존성**: STEP 03

---

### STEP 05. 인증 시스템 (JWT + RBAC)
```
참조: docs/04-auth-security.md (Section 1, 2)
```

**작업 내용**:
- `app/utils/encryption.py`: AES-256-GCM 암/복호화
- `app/dependencies.py`: `get_current_user`, `require_role` DI
- `app/schemas/auth.py`: LoginRequest, TokenResponse
- `app/services/auth_service.py`: 로그인, 토큰 발급/갱신/파기
- `app/api/v1/auth.py`: 5개 엔드포인트 (login, refresh, logout, me, oauth callback)
- Redis 세션 저장 + Token Rotation

**검증**: 로그인→토큰 발급→인증 API 호출→토큰 갱신→로그아웃 전체 플로우 테스트

**의존성**: STEP 04

---

### STEP 06. 사용자 + 클라이언트 CRUD API
```
참조: docs/02-api-endpoints.md (Section 2, 3)
```

**작업 내용**:
- `app/api/v1/users.py`: 8개 엔드포인트
- `app/api/v1/clients.py`: 13개 엔드포인트 (계정 연동, FAQ/가이드라인 포함)
- `app/services/user_service.py`, `app/services/client_service.py`
- `app/schemas/user.py`, `app/schemas/client.py`
- 역할별 접근 제어 적용

**검증**: 사용자 CRUD + 클라이언트 등록 + SNS 계정 연동 + FAQ 등록 API 테스트 통과

**의존성**: STEP 05

---

### STEP 07. 콘텐츠 관리 API + 워크플로우
```
참조: docs/02-api-endpoints.md (Section 4)
```

**작업 내용**:
- `app/api/v1/contents.py`: 10개 엔드포인트
- `app/services/content_service.py`: 상태 전이 규칙 (draft→review→client_review→approved→published)
- 워크플로우 상태 변경 시 `content_approvals` 이력 자동 생성
- `audit_logs` 자동 기록 미들웨어
- S3 Presigned URL 발급 (`/upload`)
- 캘린더 뷰 API (`/calendar`)

**검증**: 콘텐츠 생성→상태 변경(4단계)→승인 이력 확인→S3 업로드 URL 발급 테스트

**의존성**: STEP 06

---

### STEP 08. 게시 운영 + 커뮤니티 API
```
참조: docs/02-api-endpoints.md (Section 5, 6)
```

**작업 내용**:
- `app/api/v1/publishing.py`: 6개 엔드포인트
- `app/api/v1/community.py`: 8개 엔드포인트
- `app/services/publishing_service.py`: 예약/즉시 게시 로직 (Celery 연동은 STEP 14)
- `app/services/community_service.py`: 인박스 조회, 응답, 필터 규칙
- `publishing_logs` 기록

**검증**: 게시 예약/취소/이력 조회 + 인박스 필터링/응답/상태 변경 API 테스트

**의존성**: STEP 07

---

### STEP 09. 성과 분석 + 알림 + 설정 API
```
참조: docs/02-api-endpoints.md (Section 7, 9, 10)
```

**작업 내용**:
- `app/api/v1/analytics.py`: 5개 엔드포인트
- `app/api/v1/notifications.py`: 4개 엔드포인트
- `app/api/v1/settings.py`: 7개 엔드포인트
- `app/services/analytics_service.py`: KPI 집계, 트렌드 계산
- `app/services/notification_service.py`: 알림 CRUD + unread 카운터
- 감사 로그 조회 (`/settings/audit-logs`)

**검증**: 대시보드 KPI 조회 + 알림 목록/읽음처리 + 설정 변경 API 테스트

**의존성**: STEP 08

---

## Phase 2: 프론트엔드 코어 (5일)

### STEP 10. 프론트엔드 기본 구조 + 라우팅
```
참조: docs/03-frontend-architecture.md (Section 1, 8)
```

**작업 내용**:
- Tailwind CSS + shadcn/ui 초기 설정
- `src/app/Router.tsx`: 12개 라우트 정의
- `src/app/providers.tsx`: QueryClient, ThemeProvider
- `src/api/client.ts`: Axios 인스턴스 + 401 interceptor
- `src/types/index.ts`: 전체 TypeScript 타입 (API 응답 매핑)

**검증**: `pnpm dev` 기동, 빈 페이지 라우팅 동작, API 클라이언트 설정 완료

**의존성**: STEP 03

---

### STEP 11. 레이아웃 + 인증 UI
```
참조: docs/03-frontend-architecture.md (Section 4, 6), docs/04-auth-security.md
```

**작업 내용**:
- `MainLayout.tsx`: Sidebar(240px/64px) + Header + Outlet
- `Sidebar.tsx`: 8개 메뉴 아이콘+텍스트, 접힘/펼침 토글
- `Header.tsx`: ClientSwitcher + SearchBar + NotificationBell + UserMenu
- `LoginPage.tsx`: 로그인 폼 + JWT 토큰 저장
- `stores/authStore.ts`, `stores/uiStore.ts`, `stores/clientStore.ts`
- Protected Route 가드 (미인증 → /login 리다이렉트)
- 반응형: Desktop/Tablet/Mobile 3단계 대응

**검증**: 로그인→레이아웃 표시→사이드바 토글→클라이언트 전환→로그아웃 전체 플로우

**의존성**: STEP 10, STEP 05

---

### STEP 12. 대시보드 + 콘텐츠 관리 UI
```
참조: docs/03-frontend-architecture.md (Section 4)
```

**작업 내용**:
- `features/dashboard/`: KPI 카드, 트렌드 차트(Recharts), 알림 스트림, 할 일 리스트
- `features/content/ContentCalendar.tsx`: 월/주간 뷰, D&D(@dnd-kit), 상태별 색상
- `features/content/KanbanBoard.tsx`: 4컬럼 칸반 (draft→review→client_review→approved)
- `features/content/ContentEditor.tsx`: TipTap + 미디어 업로드 + AI 메타데이터 버튼
- `features/content/ContentDetail.tsx`: 상세 + ApprovalTimeline + PublishingLogs
- `features/content/PlatformPreview.tsx`: 인스타/페북/유튜브 미리보기 모킹
- React Query hooks: `useContents`, `useCreateContent`, `useUpdateStatus`

**검증**: 대시보드 데이터 표시 + 캘린더 D&D + 칸반 상태변경 + 에디터 저장 동작

**의존성**: STEP 11, STEP 07

---

### STEP 13. 게시 + 커뮤니티 + 성과 분석 UI
```
참조: docs/03-frontend-architecture.md (Section 4)
```

**작업 내용**:
- `features/publishing/`: 게시 관리 탭(전체/예약/완료/실패), 예약 설정 폼
- `features/community/UnifiedInbox.tsx`: 좌측 필터 + 중앙 스트림 + 감성 뱃지 + 응답 패널
- `features/community/SentimentDashboard.tsx`: 시계열 차트, 위기 이력 타임라인
- `features/analytics/AnalyticsDashboard.tsx`: 필터바 + KPI 카드 + 차트 + 베스트/워스트 랭킹
- `features/clients/`: 클라이언트 목록 + 상세 (계정 연동, 가이드라인 관리)
- `features/settings/`: 플랫폼 연동 상태, 워크플로우 설정, 알림 설정, 사용자 관리 (admin)

**검증**: 게시 예약→인박스 댓글 응답→성과 차트 표시→클라이언트 설정 변경 동작

**의존성**: STEP 12, STEP 08, STEP 09

---

## Phase 3: 실시간 + 비동기 (3일)

### STEP 14. Celery Worker + Beat 설정
```
참조: docs/06-async-realtime.md (Section 1)
```

**작업 내용**:
- `app/tasks/celery_app.py`: Celery 설정 + 4단계 큐 + Beat 스케줄
- `app/tasks/publishing_tasks.py`: 게시 실행 + 예약 스캔
- `app/tasks/data_collection_tasks.py`: 댓글 동기화 + KPI 수집 + 토큰 갱신
- `app/tasks/report_tasks.py`: 리포트 생성 + 뉴스레터
- Docker Compose에 celery-worker, celery-beat 서비스 추가

**검증**: `celery worker` 기동 + 예약 게시 실행 + Beat 스케줄 동작 확인

**의존성**: STEP 08

---

### STEP 15. WebSocket 실시간 통신
```
참조: docs/06-async-realtime.md (Section 2), docs/04-auth-security.md (WebSocket 인증)
```

**작업 내용**:
- `app/api/websocket.py`: ConnectionManager + JWT 검증 + 하트비트
- Redis Pub/Sub 구독 (다중 인스턴스 동기화)
- 6종 이벤트: crisis_alert, publish_result, approval_request, new_comment, notification, chat_stream
- Celery 작업 완료 시 WebSocket 푸시 연동
- `hooks/useWebSocket.ts`: 프론트엔드 WebSocket 훅 + 자동 재연결
- `features/notifications/NotificationCenter.tsx`: 드롭다운 + 실시간 업데이트
- `stores/notificationStore.ts`: unread 카운터 + WS 연결 관리

**검증**: 게시 완료 → 실시간 알림 수신 → 알림 센터 표시 → 읽음 처리 전체 플로우

**의존성**: STEP 14, STEP 13

---

## Phase 4: SNS 플랫폼 연동 (3일)

### STEP 16. Meta Graph API 연동 (Instagram + Facebook)
```
참조: docs/05-integrations.md (Section 1)
```

**작업 내용**:
- `app/integrations/meta/client.py`: MetaGraphClient (httpx async)
- `app/integrations/meta/publisher.py`: 피드/릴스/스토리 게시
- `app/integrations/meta/insights.py`: 인사이트 수집
- OAuth 플로우: 인증 코드 → 토큰 교환 → 암호화 저장
- 댓글 조회/응답 연동
- Rate Limiting, Circuit Breaker 적용

**검증**: Meta 테스트 앱으로 인스타그램 피드 게시→댓글 조회→인사이트 수집 E2E 성공

**의존성**: STEP 14

---

### STEP 17. YouTube Data API 연동
```
참조: docs/05-integrations.md (Section 1)
```

**작업 내용**:
- `app/integrations/youtube/client.py`: YouTubeClient
- `app/integrations/youtube/publisher.py`: 영상/쇼츠 업로드 (resumable)
- `app/integrations/youtube/insights.py`: 채널 통계
- OAuth 플로우 + 토큰 관리
- 댓글 조회/응답

**검증**: YouTube 테스트 채널에 영상 업로드→댓글 조회→통계 수집 성공

**의존성**: STEP 14

---

### STEP 18. 외부 API 공통 안정성 패턴
```
참조: docs/05-integrations.md (Section 3)
```

**작업 내용**:
- Circuit Breaker 범용 구현 (CLOSED→OPEN→HALF_OPEN)
- Retry with Exponential Backoff 유틸
- Redis Rate Limit 카운터 (플랫폼별 쿼터 추적)
- 토큰 자동 갱신 Celery 작업 (만료 24시간 전)
- 응답 캐싱 (Redis TTL)
- 에러 분류 + 알림 연동

**검증**: API 호출 실패 시 Circuit Breaker 동작 + 자동 재시도 + 쿼터 경고 알림 발생

**의존성**: STEP 16, STEP 17

---

## Phase 5: AI 기능 (4일)

### STEP 19. LLM 통합 클라이언트 + 카피 생성
```
참조: docs/05-integrations.md (Section 2)
```

**작업 내용**:
- `app/integrations/ai/llm_client.py`: Claude/GPT 프로바이더 추상화
- `app/api/v1/ai_tools.py`: 카피 생성 API
- 브랜드 가이드라인 System Prompt 동적 구성
- 복수 초안 생성 (3종)
- `features/ai-tools/AICopywriter.tsx`: 프론트 UI (톤 선택 + 플랫폼 선택 + 초안 목록)

**검증**: 클라이언트 브랜드 가이드 반영된 카피 3종 생성 + UI 표시

**의존성**: STEP 09

---

### STEP 20. 감성 분석 시스템
```
참조: docs/05-integrations.md (Section 2)
```

**작업 내용**:
- `app/integrations/ai/sentiment.py`: KcELECTRA 기반 4분류 (positive/neutral/negative/crisis)
- `app/tasks/ai_tasks.py`: 비동기 감성 분석 Celery 작업
- 댓글 동기화 시 자동 감성 분석 체이닝
- 부정 감성 급증 시 위기 경보 (crisis_alert) WebSocket 발송
- `SentimentDashboard.tsx`: 시계열 차트 + 위기 이력

**검증**: 댓글 수신 → 자동 감성 분류 → 부정 급증 시 위기 경보 알림 수신

**의존성**: STEP 15, STEP 19

---

### STEP 21. RAG 응대 시스템 (pgvector)
```
참조: docs/05-integrations.md (Section 2), docs/01-database.md (vector_embeddings)
```

**작업 내용**:
- `app/integrations/ai/embeddings.py`: 텍스트 청크 분할 + 벡터 생성
- `app/integrations/ai/rag.py`: RAGPipeline (유사 검색 → LLM 초안)
- FAQ/가이드라인 등록 시 벡터 자동 생성 (Celery)
- `app/api/v1/ai_tools.py`: reply-draft 엔드포인트
- 통합 인박스에서 AI 초안 버튼 연동

**검증**: FAQ 등록 → 벡터 임베딩 저장 → 댓글에 대한 RAG 응대 초안 생성 정확성 확인

**의존성**: STEP 20

---

### STEP 22. AI 챗봇 (SSE 스트리밍)
```
참조: docs/02-api-endpoints.md (AI Tools), docs/05-integrations.md
```

**작업 내용**:
- `app/api/v1/ai_tools.py`: `/ai/chat` SSE 스트리밍 엔드포인트
- Text-to-SQL: 자연어 질의 → SQL 생성 → DB 조회 → 자연어 응답
- 대화 이력 관리 (conversation_id 기반)
- `features/ai-tools/AIChatPanel.tsx`: 플로팅 패널 + 스트리밍 표시
- `stores/chatStore.ts`: 메시지 이력, 스트리밍 상태

**검증**: "지난주 인스타 베스트 게시물은?" → DB 조회 → 정확한 응답 스트리밍

**의존성**: STEP 21

---

## Phase 6: 고도화 + 품질 (3일)

### STEP 23. 파일 업로드 보안 강화
```
참조: docs/04-auth-security.md (Section 4)
```

**작업 내용**:
- `app/utils/file_validation.py`: MIME + 매직바이트 이중 검증
- 파일 크기 제한 (이미지 20MB, 영상 500MB, 문서 10MB)
- 파일명 UUID 재생성, 경로 순회 차단
- S3 Private ACL + Presigned URL 조회 (TTL: 1시간)
- 플랫폼별 자동 리사이징 (이미지: 1:1, 4:5, 9:16, 1.91:1)

**검증**: 악성 파일 업로드 차단 + 정상 파일 S3 저장 + Presigned URL 접근

**의존성**: STEP 07

---

### STEP 24. 에러 처리 + 접근성 완성
```
참조: docs/03-frontend-architecture.md (Section 5, 6, 7)
```

**작업 내용**:
- `ErrorBoundary.tsx`: 각 feature 모듈 래핑 + fallback UI
- Toast 알림 시스템 (shadcn/ui)
- 오프라인 감지 배너
- WCAG 2.1 AA: aria-label, 키보드 네비, 포커스 링, 색상 대비 4.5:1
- 반응형 최종 점검: Desktop/Tablet/Mobile 3단계

**검증**: Lighthouse Accessibility 점수 90+ / 네트워크 오프라인 시 배너 표시

**의존성**: STEP 13

---

### STEP 25. Rate Limiting + 감사 로그 미들웨어
```
참조: docs/04-auth-security.md (Section 3)
```

**작업 내용**:
- `app/middleware/rate_limiter.py`: Redis 기반 사용자/엔드포인트별
- `app/middleware/audit_middleware.py`: CUD 작업 자동 audit_logs 기록
- XSS: DOMPurify 적용 (TipTap 출력)
- CSRF: SameSite=Strict
- 슬로우 쿼리 자동 로깅 (SQLAlchemy event)

**검증**: Rate Limit 초과 → 429 응답 / 콘텐츠 수정 → audit_logs 기록 확인

**의존성**: STEP 09

---

## Phase 7: 테스트 + 배포 (3일)

### STEP 26. 백엔드 테스트 스위트
```
참조: claude.md (코드 품질 기준)
```

**작업 내용**:
- `tests/conftest.py`: 테스트 DB (SQLite async), Redis mock, 인증 fixture
- 단위 테스트: 서비스 레이어 (auth, content, publishing, community, AI mock)
- 통합 테스트: API 엔드포인트 (TestClient)
- 워크플로우 테스트: 콘텐츠 생성 → 승인 → 게시 전체 플로우
- `pytest --cov=app --cov-report=html`

**검증**: 커버리지 80% 이상, 전 테스트 통과

**의존성**: STEP 25

---

### STEP 27. 프론트엔드 테스트 스위트
```
참조: claude.md (코드 품질 기준)
```

**작업 내용**:
- Vitest + React Testing Library 설정
- 컴포넌트 테스트: 주요 feature 컴포넌트 (ContentCalendar, KanbanBoard, UnifiedInbox)
- Hook 테스트: useAuth, useWebSocket
- 통합 테스트: 로그인 → 대시보드 → 콘텐츠 생성 플로우
- MSW (Mock Service Worker)로 API mocking

**검증**: 전 테스트 통과, 주요 플로우 커버

**의존성**: STEP 24

---

### STEP 28. CI/CD 파이프라인
```
참조: docs/07-infra-devops.md (Section 5)
```

**작업 내용**:
- `.github/workflows/ci.yml`: PR 시 Lint + Type Check + Test
- `.github/workflows/deploy.yml`: main 병합 → 스테이징 자동 배포
- Docker 이미지 빌드 최적화 (multi-stage)
- `docker-compose.prod.yml`: 프로덕션 설정 (환경 변수, 리소스 제한)

**검증**: PR 생성 → CI 통과 → main 병합 → 스테이징 자동 배포 성공

**의존성**: STEP 26, STEP 27

---

### STEP 29. 모니터링 + 백업 설정
```
참조: docs/07-infra-devops.md (Section 3, 4)
```

**작업 내용**:
- Sentry 초기화 (Backend + Frontend)
- Prometheus 메트릭 엔드포인트 (`/metrics`)
- Grafana 대시보드 + 알람 규칙 (8종 지표)
- PostgreSQL 백업 (pg_dump cron + WAL 아카이빙)
- Redis 스냅샷 (1시간)
- 복구 Runbook 작성 (`docs/runbook/`)

**검증**: Sentry 에러 수집 확인 + Grafana 대시보드 메트릭 표시 + 백업 복구 테스트

**의존성**: STEP 28

---

## Phase 8: 통합 검증 (2일)

### STEP 30. E2E 통합 테스트
```
참조: 전체 문서
```

**작업 내용**:
- 시나리오 1: 콘텐츠 기획 → 제작(AI 카피) → 검수(4단계) → 게시(다중 플랫폼) → 성과 확인
- 시나리오 2: 댓글 수신 → 감성 분석 → 위기 경보 → RAG 응대 → 위기 종료
- 시나리오 3: 클라이언트 등록 → 계정 연동 → FAQ 등록 → AI 챗봇 질의
- 시나리오 4: 역할별 접근 테스트 (admin/manager/operator/client)

**검증**: 4개 시나리오 전체 통과

**의존성**: STEP 29

---

### STEP 31. 성능 + 보안 검증
```
참조: docs/04-auth-security.md, docs/07-infra-devops.md (Section 4)
```

**작업 내용**:
- API P95 응답시간 < 500ms 확인
- 동시 WebSocket 100연결 부하 테스트
- SQL Injection / XSS 취약점 스캔
- 파일 업로드 보안 검증 (악성 파일 테스트)
- Lighthouse 성능 + 접근성 점수

**검증**: 성능 목표 달성 + 보안 취약점 0건

**의존성**: STEP 30

---

## 전체 요약

| Phase | 기간 | STEP 범위 | 핵심 산출물 |
|-------|------|-----------|-----------|
| **0. 초기화** | 1일 | 01-02 | 프로젝트 구조 + Docker 인프라 |
| **1. 백엔드 코어** | 5일 | 03-09 | 14 모델, 72 API, 인증, RBAC |
| **2. 프론트엔드 코어** | 5일 | 10-13 | 12 라우트, 9 컴포넌트, 전체 UI |
| **3. 실시간+비동기** | 3일 | 14-15 | Celery 4큐, WebSocket 6이벤트 |
| **4. SNS 연동** | 3일 | 16-18 | Meta + YouTube + 안정성 패턴 |
| **5. AI 기능** | 4일 | 19-22 | LLM 카피, 감성분석, RAG, 챗봇 |
| **6. 고도화** | 3일 | 23-25 | 보안, 에러처리, Rate Limit |
| **7. 테스트+배포** | 3일 | 26-29 | 테스트 80%+, CI/CD, 모니터링 |
| **8. 통합 검증** | 2일 | 30-31 | E2E 시나리오, 성능, 보안 |
| **총계** | **~29일** | **31 STEP** | **MVP 완성** |

---

## 의존성 그래프 (요약)

```
STEP 01 → STEP 02 → STEP 03 → STEP 04 → STEP 05 → STEP 06 → STEP 07 → STEP 08 → STEP 09
                       ↓                                                          ↓
                    STEP 10 → STEP 11 → STEP 12 → STEP 13 ─────────────────→ STEP 24
                                                    ↓
                    STEP 14 ──→ STEP 15 ──→ STEP 16 → STEP 17 → STEP 18
                       ↓            ↓
                    STEP 19 → STEP 20 → STEP 21 → STEP 22
                                                    ↓
                    STEP 23, STEP 25 ──→ STEP 26 → STEP 27 → STEP 28 → STEP 29 → STEP 30 → STEP 31
```

> **병렬 가능**: Phase 2 (프론트엔드)와 Phase 1 후반(백엔드 API)은 API 스펙 확정 후 병렬 진행 가능.
> Phase 4 (SNS 연동)와 Phase 5 (AI)도 일부 병렬 가능.
