# 02. API 엔드포인트 설계

## 설계 원칙

- **RESTful**: URL은 리소스 중심, HTTP 메서드로 행위 구분
- **버전 관리**: `/api/v1/` 프리픽스
- **응답 표준화**: `{ status: "success"|"error", data, message, pagination? }`
- **오류 표준화**: RFC 7807 Problem Details — `{ type, title, status, detail, instance }`
- **인증**: Bearer Token (JWT) — auth 엔드포인트 제외 전체 필수
- **페이지네이션**: cursor 기반 (무한스크롤) + offset 기반 (페이지) 복합

```python
# 표준 응답 스키마
class APIResponse(BaseModel):
    status: Literal["success", "error"]
    data: Any = None
    message: str | None = None
    pagination: PaginationMeta | None = None

class PaginationMeta(BaseModel):
    total: int
    page: int | None = None       # offset 방식
    per_page: int | None = None
    cursor: str | None = None     # cursor 방식
    has_next: bool
```

---

## 1. 인증 (Auth) — 5 endpoints

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| POST | `/api/v1/auth/login` | 로그인 → Access + Refresh 토큰 발급 | Public |
| POST | `/api/v1/auth/refresh` | Refresh 토큰 → 새 Access 토큰 | Public |
| POST | `/api/v1/auth/logout` | 로그아웃 + Redis 세션 파기 | 인증 |
| GET | `/api/v1/auth/me` | 현재 사용자 정보 조회 | 인증 |
| POST | `/api/v1/auth/oauth/{platform}/callback` | SNS OAuth 콜백 처리 | 인증 |

```python
# POST /api/v1/auth/login
# Request
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Response 200
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30분
```

---

## 2. 사용자 관리 (Users) — 8 endpoints

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/users` | 사용자 목록 (필터: role, is_active) | admin |
| POST | `/api/v1/users` | 사용자 생성 | admin |
| GET | `/api/v1/users/{id}` | 사용자 상세 조회 | admin, manager |
| PUT | `/api/v1/users/{id}` | 사용자 정보 수정 | admin |
| PATCH | `/api/v1/users/{id}/role` | 역할 변경 | admin |
| PATCH | `/api/v1/users/{id}/active` | 활성/비활성 토글 | admin |
| PUT | `/api/v1/users/me/profile` | 내 프로필 수정 | 인증 |
| PUT | `/api/v1/users/me/password` | 비밀번호 변경 | 인증 |

```python
# POST /api/v1/users
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(max_length=100)
    role: UserRole
    client_ids: list[UUID] | None = None  # client 역할일 때

# GET /api/v1/users?role=operator&is_active=true&page=1&per_page=20
class UserFilter(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    search: str | None = None  # 이름/이메일 검색
```

---

## 3. 클라이언트 관리 (Clients) — 13 endpoints

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/clients` | 목록 (필터: status, industry, manager_id) | admin, manager, operator(배정) |
| POST | `/api/v1/clients` | 신규 등록 | admin, manager |
| GET | `/api/v1/clients/{id}` | 상세 (연동 계정, 가이드라인 포함) | admin, manager, operator(배정) |
| PUT | `/api/v1/clients/{id}` | 정보 수정 | admin, manager |
| PATCH | `/api/v1/clients/{id}/status` | 상태 변경 (active↔paused↔archived) | admin, manager |
| PUT | `/api/v1/clients/{id}/brand-guidelines` | 브랜드 가이드라인 업데이트 | admin, manager |
| GET | `/api/v1/clients/{id}/accounts` | 연동 SNS 계정 목록 | admin, manager, operator |
| POST | `/api/v1/clients/{id}/accounts` | SNS 계정 연동 추가 | admin, manager |
| DELETE | `/api/v1/clients/{id}/accounts/{accountId}` | SNS 계정 연동 해제 | admin, manager |
| GET | `/api/v1/clients/{id}/faq-guidelines` | FAQ/가이드라인 목록 | admin, manager, operator |
| POST | `/api/v1/clients/{id}/faq-guidelines` | FAQ/가이드라인 등록 | admin, manager, operator |
| PUT | `/api/v1/clients/{id}/faq-guidelines/{faqId}` | FAQ/가이드라인 수정 | admin, manager, operator |
| DELETE | `/api/v1/clients/{id}/faq-guidelines/{faqId}` | FAQ/가이드라인 삭제 | admin, manager |

```python
# POST /api/v1/clients
class ClientCreate(BaseModel):
    name: str = Field(max_length=200)
    industry: str | None = None
    manager_id: UUID
    contract_start: date | None = None
    contract_end: date | None = None

# PUT /api/v1/clients/{id}/brand-guidelines
class BrandGuidelinesUpdate(BaseModel):
    tone: str | None = None           # "친근하고 활발한"
    color_palette: list[str] | None   # ["#FF6B35", "#004E89"]
    forbidden_words: list[str] | None # ["경쟁사명", "비속어"]
    voice_profile: str | None = None  # 브랜드 보이스 설명

# POST /api/v1/clients/{id}/faq-guidelines
class FaqGuidelineCreate(BaseModel):
    category: Literal["faq", "tone_manner", "crisis_scenario", "template"]
    title: str = Field(max_length=300)
    content: str
    tags: list[str] | None = None
    priority: int = 0
```

---

## 4. 콘텐츠 관리 (Contents) — 10 endpoints

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/contents` | 목록 (필터: status, client, platform, date) | 인증 |
| POST | `/api/v1/contents` | 생성 (draft 상태로 시작) | admin, manager, operator |
| GET | `/api/v1/contents/{id}` | 상세 (승인 이력, 게시 로그 포함) | 인증 |
| PUT | `/api/v1/contents/{id}` | 수정 | admin, manager, operator |
| DELETE | `/api/v1/contents/{id}` | 삭제 (draft 상태만) | admin, manager, operator |
| PATCH | `/api/v1/contents/{id}/status` | 상태 변경 (워크플로우 단계별) | 역할별 |
| GET | `/api/v1/contents/calendar` | 캘린더 뷰 (기간별 리스트) | 인증 |
| POST | `/api/v1/contents/{id}/upload` | S3 Presigned URL 발급 | admin, manager, operator |
| GET | `/api/v1/contents/{id}/approvals` | 승인 이력 조회 | 인증 |
| GET | `/api/v1/contents/{id}/publishing-logs` | 게시 이력 조회 | 인증 |

```python
# POST /api/v1/contents
class ContentCreate(BaseModel):
    client_id: UUID
    title: str = Field(max_length=500)
    body: str | None = None
    content_type: ContentType       # feed, reel, story, short, card_news
    target_platforms: list[str]     # ["instagram", "facebook"]
    hashtags: list[str] | None = None
    scheduled_at: datetime | None = None

# PATCH /api/v1/contents/{id}/status — 워크플로우 전이 규칙
# operator: draft → review
# manager: review → client_review, rejected → draft
# client: client_review → approved | rejected
# system: approved → published (게시 완료 시)
class StatusChangeRequest(BaseModel):
    to_status: ContentStatus
    comment: str | None = None      # 반려 사유 등
    is_urgent: bool = False         # 긴급 승인 (단계 생략)

# GET /api/v1/contents/calendar?client_id=...&start=2026-02-01&end=2026-02-28
class CalendarQuery(BaseModel):
    client_id: UUID | None = None
    start: date
    end: date
    platform: str | None = None
```

---

## 5. 게시 운영 (Publishing) — 6 endpoints

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| POST | `/api/v1/publishing/schedule` | 예약 게시 (Celery 작업 등록) | admin, manager, operator |
| POST | `/api/v1/publishing/now` | 즉시 게시 (다중 플랫폼 동시) | admin, manager, operator |
| GET | `/api/v1/publishing/queue` | 게시 대기열 조회 | 인증 |
| DELETE | `/api/v1/publishing/{id}/cancel` | 예약 게시 취소 | admin, manager, operator |
| GET | `/api/v1/publishing/history` | 게시 이력 (필터: status, platform, date) | 인증 |
| POST | `/api/v1/publishing/{id}/retry` | 실패 게시 재시도 | admin, manager, operator |

```python
# POST /api/v1/publishing/schedule
class ScheduleRequest(BaseModel):
    content_id: UUID
    platform_account_ids: list[UUID]  # 게시할 플랫폼 계정들
    scheduled_at: datetime            # UTC 예약 시간

# POST /api/v1/publishing/now
class PublishNowRequest(BaseModel):
    content_id: UUID
    platform_account_ids: list[UUID]
```

---

## 6. 커뮤니티 관리 (Community) — 8 endpoints

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/community/inbox` | 통합 인박스 (필터: sentiment, status, platform) | admin, manager, operator |
| POST | `/api/v1/community/{id}/reply` | 댓글 응답 | admin, manager, operator |
| PATCH | `/api/v1/community/{id}/status` | 댓글 상태 변경 (hide, flag) | admin, manager, operator |
| GET | `/api/v1/community/sentiment` | 감성 분석 통계 | 인증 |
| GET | `/api/v1/community/filter-rules` | 자동 필터/차단 규칙 목록 | admin, manager |
| POST | `/api/v1/community/filter-rules` | 자동 필터 규칙 등록 | admin, manager |
| PUT | `/api/v1/community/filter-rules/{id}` | 자동 필터 규칙 수정 | admin, manager |
| DELETE | `/api/v1/community/filter-rules/{id}` | 자동 필터 규칙 삭제 | admin, manager |

```python
# GET /api/v1/community/inbox?sentiment=negative&status=pending&cursor=...
class InboxFilter(BaseModel):
    client_id: UUID | None = None
    platform: str | None = None
    sentiment: Sentiment | None = None
    status: CommentStatus | None = None
    cursor: str | None = None
    per_page: int = 20

# POST /api/v1/community/{id}/reply
class ReplyRequest(BaseModel):
    message: str                      # 응답 텍스트
    use_ai_draft: bool = False        # AI 초안 사용 여부

# POST /api/v1/community/filter-rules
class FilterRuleCreate(BaseModel):
    client_id: UUID
    rule_type: Literal["keyword", "pattern", "user_block"]
    value: str                        # 키워드 또는 정규식
    action: Literal["hide", "flag", "delete"]
    is_active: bool = True
```

---

## 7. 성과 분석 (Analytics) — 5 endpoints

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/analytics/dashboard` | KPI 요약 (도달, 참여율, 팔로워) | 인증 |
| GET | `/api/v1/analytics/trends` | 기간별 성과 추이 | 인증 |
| GET | `/api/v1/analytics/content-perf` | 콘텐츠 유형별 성과 비교 | 인증 |
| POST | `/api/v1/analytics/report` | AI 인사이트 리포트 생성 (비동기) | admin, manager |
| GET | `/api/v1/analytics/report/{id}` | 리포트 조회/다운로드 | 인증 |

```python
# GET /api/v1/analytics/dashboard?client_id=...&period=30d
class DashboardQuery(BaseModel):
    client_id: UUID | None = None
    platform: str | None = None
    period: Literal["7d", "30d", "90d"] = "30d"

# Response
class DashboardKPI(BaseModel):
    reach: MetricWithChange           # { value, change_percent, trend }
    engagement_rate: MetricWithChange
    follower_change: MetricWithChange
    video_views: MetricWithChange
    top_content: list[ContentSummary]
    worst_content: list[ContentSummary]
```

---

## 8. AI 도구 (AI Tools) — 6 endpoints

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| POST | `/api/v1/ai/copy-generate` | AI 카피/캡션 생성 | admin, manager, operator |
| POST | `/api/v1/ai/metadata-generate` | AI 메타데이터 생성 (해시태그, 캡션) | admin, manager, operator |
| POST | `/api/v1/ai/sentiment-analyze` | 댓글 감성 분석 요청 | admin, manager, operator |
| POST | `/api/v1/ai/reply-draft` | RAG 기반 응대 초안 생성 | admin, manager, operator |
| POST | `/api/v1/ai/optimal-time` | 최적 게시 시간 추천 | admin, manager, operator |
| POST | `/api/v1/ai/chat` | AI 질의 챗봇 (SSE Streaming) | 인증 |

```python
# POST /api/v1/ai/copy-generate
class CopyGenerateRequest(BaseModel):
    client_id: UUID
    platform: str
    topic: str
    tone: str | None = None           # brand_guidelines에서 자동 로드
    content_type: ContentType
    num_variants: int = 3             # 복수 초안 수

# POST /api/v1/ai/reply-draft
class ReplyDraftRequest(BaseModel):
    comment_id: UUID                  # 대상 댓글
    client_id: UUID                   # FAQ/가이드라인 검색 범위

# POST /api/v1/ai/chat — SSE Streaming Response
class ChatRequest(BaseModel):
    message: str
    client_id: UUID | None = None     # 컨텍스트 제한
    conversation_id: str | None = None  # 대화 이력 연결
```

---

## 9. 알림 (Notifications) — 4 endpoints

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/notifications` | 알림 목록 (필터: type, is_read, priority) | 인증 |
| GET | `/api/v1/notifications/unread-count` | 읽지 않은 알림 수 | 인증 |
| PATCH | `/api/v1/notifications/{id}/read` | 개별 읽음 처리 | 인증 |
| PATCH | `/api/v1/notifications/read-all` | 전체 읽음 처리 | 인증 |

```python
# GET /api/v1/notifications?type=crisis_alert&is_read=false&cursor=...
class NotificationFilter(BaseModel):
    type: NotificationType | None = None
    is_read: bool | None = None
    priority: NotificationPriority | None = None
    cursor: str | None = None
    per_page: int = 20
```

---

## 10. 설정 (Settings) — 7 endpoints

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/settings/platform-connections` | 플랫폼 API 연동 상태 | admin, manager |
| POST | `/api/v1/settings/platform-connections/test` | 플랫폼 API 연결 테스트 | admin, manager |
| GET | `/api/v1/settings/workflows` | 워크플로우 설정 (검수 단계, 자동화) | admin, manager |
| PUT | `/api/v1/settings/workflows` | 워크플로우 설정 변경 | admin |
| GET | `/api/v1/settings/notification-preferences` | 알림 설정 (슬랙/카카오톡/이메일) | 인증 |
| PUT | `/api/v1/settings/notification-preferences` | 알림 설정 변경 | 인증 |
| GET | `/api/v1/settings/audit-logs` | 감사 로그 조회 | admin, manager |

```python
# PUT /api/v1/settings/workflows
class WorkflowSettings(BaseModel):
    approval_steps: list[str]         # ["review", "client_review"]
    auto_publish_on_approve: bool = False
    urgent_skip_enabled: bool = True
    notification_channels: dict       # {"approval": ["slack", "email"]}

# PUT /api/v1/settings/notification-preferences
class NotificationPreferences(BaseModel):
    email_enabled: bool = True
    slack_webhook_url: str | None = None
    kakao_enabled: bool = False
    crisis_alert: list[str] = ["email", "slack"]  # 위기경보 수신 채널
    approval_request: list[str] = ["email"]
    publish_result: list[str] = ["email"]
```

---

## API 라우터 등록 (main.py)

```python
from fastapi import FastAPI
from app.api.v1 import (
    auth, users, clients, contents, publishing,
    community, analytics, ai_tools, notifications, settings
)

app = FastAPI(title="SNS 통합 관리 솔루션", version="1.0.0")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["Clients"])
app.include_router(contents.router, prefix="/api/v1/contents", tags=["Contents"])
app.include_router(publishing.router, prefix="/api/v1/publishing", tags=["Publishing"])
app.include_router(community.router, prefix="/api/v1/community", tags=["Community"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(ai_tools.router, prefix="/api/v1/ai", tags=["AI Tools"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
```

**총 72개 REST 엔드포인트** (Auth 5 + Users 8 + Clients 13 + Contents 10 + Publishing 6 + Community 8 + Analytics 5 + AI 6 + Notifications 4 + Settings 7)

---

## WebSocket 엔드포인트

| 프로토콜 | 엔드포인트 | 설명 | 인증 |
|---------|-----------|------|------|
| WS | `/ws?token={access_token}` | 실시간 알림, 위기경보, 게시결과, 댓글 스트림 | JWT query param |

> WebSocket 상세 설계(이벤트 유형, ConnectionManager, 하트비트, Redis Pub/Sub)는 `docs/06-async-realtime.md` Section 2 참조.
