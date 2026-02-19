# 01. 데이터베이스 설계

## PostgreSQL 16 + pgvector

모든 테이블 공통: `id` UUID PK (gen_random_uuid()), `created_at` TIMESTAMPTZ DEFAULT now(), `updated_at` TIMESTAMPTZ (트리거 자동갱신).

---

## 1. 핵심 테이블 (6종)

### users

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| email | VARCHAR(255) | UNIQUE NOT NULL | 로그인 이메일 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 해시 |
| name | VARCHAR(100) | NOT NULL | 사용자 이름 |
| role | ENUM('admin','manager','operator','client') | NOT NULL | 역할 |
| is_active | BOOLEAN | DEFAULT true | 활성 상태 |
| avatar_url | VARCHAR(500) | NULL | 프로필 이미지 |
| last_login_at | TIMESTAMPTZ | NULL | 마지막 로그인 |

### clients

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| name | VARCHAR(200) | NOT NULL | 클라이언트명 |
| industry | VARCHAR(100) | NULL | 업종 (F&B, IT, 패션 등) |
| brand_guidelines | JSONB | NULL | 브랜드 가이드라인 (톤, 컬러, 금지어) |
| logo_url | VARCHAR(500) | NULL | 로고 URL |
| manager_id | UUID | FK → users | 담당 관리자 |
| status | ENUM('active','paused','archived') | NOT NULL | 상태 |
| contract_start | DATE | NULL | 계약 시작일 |
| contract_end | DATE | NULL | 계약 종료일 |

### platform_accounts

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| client_id | UUID | FK → clients | 소속 클라이언트 |
| platform | ENUM('instagram','facebook','youtube') | NOT NULL | 플랫폼 |
| account_name | VARCHAR(200) | NOT NULL | 계정명 (@handle) |
| access_token | TEXT | NOT NULL | OAuth 토큰 (AES-256-GCM 암호화) |
| refresh_token | TEXT | NULL | 리프레시 토큰 (AES-256-GCM 암호화) |
| token_expires_at | TIMESTAMPTZ | NULL | 토큰 만료 시간 |
| is_connected | BOOLEAN | DEFAULT true | 연동 상태 |

### contents

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| client_id | UUID | FK → clients | 소속 클라이언트 |
| title | VARCHAR(500) | NOT NULL | 제목 |
| body | TEXT | NULL | 본문 (카피/캡션) |
| content_type | ENUM('feed','reel','story','short','card_news') | NOT NULL | 유형 |
| status | ENUM('draft','review','client_review','approved','published','rejected') | NOT NULL | 상태 |
| media_urls | JSONB | NULL | 미디어 URL 배열 |
| hashtags | VARCHAR[] | NULL | 해시태그 배열 |
| target_platforms | VARCHAR[] | NOT NULL | 게시 대상 플랫폼 |
| scheduled_at | TIMESTAMPTZ | NULL | 예약 게시 시간 |
| published_at | TIMESTAMPTZ | NULL | 실제 게시 시간 |
| approved_at | TIMESTAMPTZ | NULL | 최종 승인 시간 |
| approved_by | UUID | FK → users NULL | 최종 승인자 |
| ai_metadata | JSONB | NULL | AI 메타데이터 (추천 해시태그, 최적 시간) |
| created_by | UUID | FK → users | 작성자 |

### comments_inbox

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| platform_account_id | UUID | FK → platform_accounts | 연동 계정 |
| content_id | UUID | FK → contents NULL | 원본 콘텐츠 |
| platform_comment_id | VARCHAR(200) | NOT NULL | 플랫폼 댓글 ID |
| parent_comment_id | UUID | FK (self) NULL | 부모 댓글 (대댓글) |
| author_name | VARCHAR(200) | NOT NULL | 작성자명 |
| author_profile_url | VARCHAR(500) | NULL | 작성자 프로필 URL |
| message | TEXT | NOT NULL | 댓글 내용 |
| sentiment | ENUM('positive','neutral','negative','crisis') | NULL | AI 감성분류 |
| sentiment_score | FLOAT | NULL | 감성 점수 (-1.0 ~ 1.0) |
| status | ENUM('pending','replied','hidden','flagged') | NOT NULL DEFAULT 'pending' | 처리 상태 |
| ai_reply_draft | TEXT | NULL | AI 응대 초안 |
| replied_at | TIMESTAMPTZ | NULL | 응답 시간 |
| replied_by | UUID | FK → users NULL | 응답 담당자 |
| commented_at | TIMESTAMPTZ | NOT NULL | 원본 댓글 작성 시간 |

### analytics_snapshots

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| platform_account_id | UUID | FK → platform_accounts | 연동 계정 |
| snapshot_date | DATE | NOT NULL | 스냅샷 날짜 |
| metrics | JSONB | NOT NULL | {reach, engagement, followers, impressions, ...} |
| content_id | UUID | FK → contents NULL | 콘텐츠별 성과 연결 |

`UNIQUE(platform_account_id, snapshot_date, content_id)` — 중복 방지.

---

## 2. 추가 테이블 (8종)

### user_client_assignments (사용자-클라이언트 배정)

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| user_id | UUID | FK → users NOT NULL | 배정 사용자 |
| client_id | UUID | FK → clients NOT NULL | 배정 클라이언트 |
| role_in_client | ENUM('manager','operator','viewer') | NOT NULL | 클라이언트 내 역할 |
| assigned_at | TIMESTAMPTZ | DEFAULT now() | 배정일 |

`UNIQUE(user_id, client_id)` — 동일 사용자-클라이언트 중복 배정 방지.

### filter_rules (커뮤니티 자동 필터 규칙)

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| client_id | UUID | FK → clients NOT NULL | 소속 클라이언트 |
| rule_type | ENUM('keyword','pattern','user_block') | NOT NULL | 규칙 유형 |
| value | VARCHAR(500) | NOT NULL | 키워드 또는 정규식 |
| action | ENUM('hide','flag','delete') | NOT NULL | 자동 처리 동작 |
| is_active | BOOLEAN | DEFAULT true | 활성 여부 |

### notifications

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| user_id | UUID | FK → users | 수신 대상 |
| type | ENUM('approval_request','publish_result','crisis_alert','comment','system') | NOT NULL | 유형 |
| title | VARCHAR(200) | NOT NULL | 알림 제목 |
| message | TEXT | NOT NULL | 알림 내용 |
| reference_type | VARCHAR(50) | NULL | 참조 엔티티 타입 |
| reference_id | UUID | NULL | 참조 엔티티 ID |
| is_read | BOOLEAN | DEFAULT false | 읽음 여부 |
| read_at | TIMESTAMPTZ | NULL | 읽음 시간 |
| priority | ENUM('low','normal','high','critical') | DEFAULT 'normal' | 우선순위 |

### audit_logs

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| user_id | UUID | FK → users | 수행자 |
| action | ENUM('create','update','delete','approve','reject','publish','login','logout') | NOT NULL | 액션 |
| entity_type | VARCHAR(50) | NOT NULL | 대상 타입 |
| entity_id | UUID | NULL | 대상 ID |
| changes | JSONB | NULL | 변경 diff {before, after} |
| ip_address | VARCHAR(45) | NULL | 요청 IP |
| user_agent | VARCHAR(500) | NULL | UA |

### content_approvals

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| content_id | UUID | FK → contents | 대상 콘텐츠 |
| from_status | ENUM | NOT NULL | 이전 상태 |
| to_status | ENUM | NOT NULL | 변경 후 상태 |
| reviewer_id | UUID | FK → users | 검수자 |
| comment | TEXT | NULL | 승인 코멘트 / 반려 사유 |
| is_urgent | BOOLEAN | DEFAULT false | 긴급 승인 여부 |

### publishing_logs

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| content_id | UUID | FK → contents | 대상 콘텐츠 |
| platform_account_id | UUID | FK → platform_accounts | 게시 대상 계정 |
| status | ENUM('pending','publishing','success','failed','cancelled') | NOT NULL | 상태 |
| platform_post_id | VARCHAR(200) | NULL | 플랫폼 게시물 ID |
| platform_post_url | VARCHAR(500) | NULL | 게시물 URL |
| error_message | TEXT | NULL | 실패 사유 |
| retry_count | INTEGER | DEFAULT 0 | 재시도 횟수 |
| scheduled_at | TIMESTAMPTZ | NULL | 예약 시간 |
| published_at | TIMESTAMPTZ | NULL | 실제 게시 시간 |
| celery_task_id | VARCHAR(200) | NULL | Celery 작업 ID |

### faq_guidelines

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| client_id | UUID | FK → clients | 소속 클라이언트 |
| category | ENUM('faq','tone_manner','crisis_scenario','template') | NOT NULL | 분류 |
| title | VARCHAR(300) | NOT NULL | 제목 |
| content | TEXT | NOT NULL | 본문 |
| tags | VARCHAR[] | NULL | 검색용 태그 |
| is_active | BOOLEAN | DEFAULT true | 활성 |
| priority | INTEGER | DEFAULT 0 | 표시 순서 |

### vector_embeddings (pgvector)

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 고유 식별자 |
| source_type | VARCHAR(50) | NOT NULL | 원본 타입 |
| source_id | UUID | NOT NULL | 원본 ID |
| chunk_index | INTEGER | NOT NULL | 청크 순서 |
| chunk_text | TEXT | NOT NULL | 텍스트 청크 |
| embedding | vector(1536) | NOT NULL | 임베딩 벡터 |
| metadata | JSONB | NULL | {client_id, category} |

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## 3. 인덱스 전략 (14종)

```sql
-- contents
CREATE INDEX idx_contents_client_status ON contents(client_id, status);
CREATE INDEX idx_contents_scheduled ON contents(scheduled_at) WHERE status = 'approved';
CREATE INDEX idx_contents_calendar ON contents(client_id, scheduled_at);

-- comments_inbox
CREATE INDEX idx_comments_account_status ON comments_inbox(platform_account_id, status);
CREATE INDEX idx_comments_sentiment_negative ON comments_inbox(sentiment) WHERE sentiment = 'negative';
CREATE INDEX idx_comments_sentiment_crisis ON comments_inbox(sentiment) WHERE sentiment = 'crisis';

-- analytics_snapshots
CREATE INDEX idx_analytics_account_date ON analytics_snapshots(platform_account_id, snapshot_date);

-- notifications
CREATE INDEX idx_notif_user_unread ON notifications(user_id, is_read) WHERE is_read = false;

-- publishing_logs
CREATE INDEX idx_publog_content ON publishing_logs(content_id, status);

-- content_approvals
CREATE INDEX idx_approval_content ON content_approvals(content_id, created_at);

-- vector_embeddings (pgvector)
CREATE INDEX idx_vector_ivfflat ON vector_embeddings USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- audit_logs
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id, created_at);

-- user_client_assignments
CREATE INDEX idx_uca_user ON user_client_assignments(user_id);
CREATE INDEX idx_uca_client ON user_client_assignments(client_id);

-- filter_rules
CREATE INDEX idx_filter_client_active ON filter_rules(client_id) WHERE is_active = true;
```

---

## 4. Redis 데이터 구조 (10종)

| Key 패턴 | 타입 | 용도 | TTL |
|----------|------|------|-----|
| `session:{user_id}` | Hash | JWT 세션, Refresh 토큰 | 7일 |
| `cache:api:{hash}` | String | SNS API 응답 캐싱 | 5분 |
| `cache:analytics:{account_id}:{date}` | Hash | 성과 데이터 캐시 | 1시간 |
| `queue:publish` | List | SNS 게시 Celery 큐 | - |
| `queue:ai` | List | AI 처리 Celery 큐 | - |
| `pubsub:notifications` | Channel | 실시간 알림 | - |
| `pubsub:crisis:{client_id}` | Channel | 위기 경보 브로드캐스트 | - |
| `ratelimit:{user_id}:{endpoint}` | String | Rate Limiting 카운터 | 1분 |
| `online:{user_id}` | String | 사용자 온라인 상태 | 5분 |
| `notif:unread:{user_id}` | String | 읽지 않은 알림 카운터 | 영구 |
