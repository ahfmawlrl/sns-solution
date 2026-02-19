# 데이터베이스 스키마 정의서

> **DB**: PostgreSQL 16 + pgvector
> **생성 기준**: `alembic upgrade head` (migration `001_initial_schema`)
> **최종 확인**: 2026-02-19

---

## 목차

1. [ENUM 타입](#1-enum-타입)
2. [테이블 목록](#2-테이블-목록)
3. [테이블 상세](#3-테이블-상세)
   - [users](#31-users--사용자)
   - [clients](#32-clients--클라이언트)
   - [user_client_assignments](#33-user_client_assignments--사용자-클라이언트-배정)
   - [platform_accounts](#34-platform_accounts--sns-플랫폼-계정)
   - [contents](#35-contents--콘텐츠)
   - [content_approvals](#36-content_approvals--콘텐츠-승인-이력)
   - [publishing_logs](#37-publishing_logs--게시-로그)
   - [comments_inbox](#38-comments_inbox--댓글-수신함)
   - [analytics_snapshots](#39-analytics_snapshots--분석-스냅샷)
   - [notifications](#310-notifications--알림)
   - [audit_logs](#311-audit_logs--감사-로그)
   - [faq_guidelines](#312-faq_guidelines--faq--가이드라인)
   - [filter_rules](#313-filter_rules--필터-규칙)
   - [vector_embeddings](#314-vector_embeddings--벡터-임베딩)
4. [인덱스 목록](#4-인덱스-목록)
5. [외래키 관계](#5-외래키-관계)
6. [ERD 요약](#6-erd-요약)

---

## 1. ENUM 타입

| ENUM 이름 | 값 | 설명 |
|-----------|-----|------|
| `user_role` | `admin`, `manager`, `operator`, `client` | 시스템 사용자 역할 |
| `client_status` | `active`, `paused`, `archived` | 클라이언트 계약 상태 |
| `role_in_client` | `manager`, `operator`, `viewer` | 클라이언트별 사용자 역할 |
| `platform` | `instagram`, `facebook`, `youtube` | 지원 SNS 플랫폼 |
| `content_type` | `feed`, `reel`, `story`, `short`, `card_news` | 콘텐츠 유형 |
| `content_status` | `draft`, `review`, `client_review`, `approved`, `published`, `rejected` | 콘텐츠 워크플로 상태 |
| `publishing_status` | `pending`, `publishing`, `success`, `failed`, `cancelled` | 게시 작업 상태 |
| `comment_status` | `pending`, `replied`, `hidden`, `flagged` | 댓글 처리 상태 |
| `sentiment` | `positive`, `neutral`, `negative`, `crisis` | AI 감성 분석 결과 |
| `notification_type` | `approval_request`, `publish_result`, `crisis_alert`, `comment`, `system` | 알림 유형 |
| `notification_priority` | `low`, `normal`, `high`, `critical` | 알림 우선순위 |
| `audit_action` | `create`, `update`, `delete`, `approve`, `reject`, `publish`, `login`, `logout` | 감사 로그 액션 |
| `faq_category` | `faq`, `tone_manner`, `crisis_scenario`, `template` | FAQ/가이드라인 카테고리 |
| `rule_type` | `keyword`, `pattern`, `user_block` | 필터 규칙 유형 |
| `filter_action` | `hide`, `flag`, `delete` | 필터 적용 액션 |

---

## 2. 테이블 목록

| # | 테이블명 | 설명 | 레코드 성격 |
|---|----------|------|------------|
| 1 | `users` | 시스템 사용자 계정 | 마스터 |
| 2 | `clients` | SNS 운영 대행 클라이언트(브랜드) | 마스터 |
| 3 | `user_client_assignments` | 사용자↔클라이언트 담당 배정 | 관계 |
| 4 | `platform_accounts` | 클라이언트의 SNS 플랫폼 연동 계정 | 마스터 |
| 5 | `contents` | 콘텐츠 기획/제작/승인/게시 전 주기 | 핵심 트랜잭션 |
| 6 | `content_approvals` | 콘텐츠 상태 변경 승인/반려 이력 | 이력 |
| 7 | `publishing_logs` | 플랫폼 게시 작업 실행 로그 | 이력 |
| 8 | `comments_inbox` | 수집된 SNS 댓글 통합 수신함 | 트랜잭션 |
| 9 | `analytics_snapshots` | 플랫폼 성과 지표 일별 스냅샷 | 시계열 |
| 10 | `notifications` | 사용자 인앱 알림 | 트랜잭션 |
| 11 | `audit_logs` | 전체 CUD·승인·게시 감사 로그 | 이력 |
| 12 | `faq_guidelines` | 클라이언트별 FAQ 및 브랜드 가이드라인 | 마스터 |
| 13 | `filter_rules` | 댓글 자동 필터 규칙 | 마스터 |
| 14 | `vector_embeddings` | RAG용 텍스트 벡터 임베딩 | AI 보조 |

---

## 3. 테이블 상세

### 3.1 `users` — 사용자

시스템에 로그인하는 모든 사용자(내부 직원 + 클라이언트 담당자).

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `email` | `varchar(255)` | NO | — | 이메일 (로그인 ID, UNIQUE) |
| `password_hash` | `varchar(255)` | NO | — | bcrypt 해시 비밀번호 |
| `name` | `varchar(100)` | NO | — | 표시 이름 |
| `role` | `user_role` | NO | — | 시스템 역할 (`admin`/`manager`/`operator`/`client`) |
| `is_active` | `boolean` | YES | `true` | 계정 활성 여부 |
| `avatar_url` | `varchar(500)` | YES | — | 프로필 이미지 URL |
| `last_login_at` | `timestamptz` | YES | — | 마지막 로그인 시각 |
| `created_at` | `timestamptz` | YES | `now()` | 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

**제약**: `UNIQUE(email)`

---

### 3.2 `clients` — 클라이언트

SNS 운영을 대행하는 브랜드/고객사 정보.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `name` | `varchar(200)` | NO | — | 클라이언트(브랜드) 이름 |
| `industry` | `varchar(100)` | YES | — | 업종 (예: 패션, 식품) |
| `brand_guidelines` | `jsonb` | YES | — | 브랜드 가이드라인 (톤앤매너, 금지어 등) JSON |
| `logo_url` | `varchar(500)` | YES | — | 로고 이미지 URL |
| `manager_id` | `uuid` | NO | — | FK → `users.id` (담당 매니저) |
| `status` | `client_status` | NO | `'active'` | 계약 상태 (`active`/`paused`/`archived`) |
| `contract_start` | `date` | YES | — | 계약 시작일 |
| `contract_end` | `date` | YES | — | 계약 종료일 |
| `created_at` | `timestamptz` | YES | `now()` | 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

---

### 3.3 `user_client_assignments` — 사용자-클라이언트 배정

어떤 사용자가 어떤 클라이언트를 담당하는지 매핑. 동일 사용자가 여러 클라이언트 담당 가능.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `user_id` | `uuid` | NO | — | FK → `users.id` |
| `client_id` | `uuid` | NO | — | FK → `clients.id` |
| `role_in_client` | `role_in_client` | NO | — | 해당 클라이언트 내 역할 (`manager`/`operator`/`viewer`) |
| `assigned_at` | `timestamptz` | YES | `now()` | 배정 시각 |

**제약**: `UNIQUE(user_id, client_id)` — 동일 클라이언트에 중복 배정 불가

---

### 3.4 `platform_accounts` — SNS 플랫폼 계정

클라이언트가 연동한 Instagram·Facebook·YouTube 계정 및 OAuth 토큰.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `client_id` | `uuid` | NO | — | FK → `clients.id` |
| `platform` | `platform` | NO | — | 플랫폼 종류 (`instagram`/`facebook`/`youtube`) |
| `account_name` | `varchar(200)` | NO | — | 계정명 (핸들/채널명) |
| `access_token` | `text` | NO | — | AES-256-GCM 암호화된 OAuth Access Token |
| `refresh_token` | `text` | YES | — | AES-256-GCM 암호화된 Refresh Token |
| `token_expires_at` | `timestamptz` | YES | — | Access Token 만료 시각 |
| `is_connected` | `boolean` | YES | `true` | 연동 활성 여부 |
| `created_at` | `timestamptz` | YES | `now()` | 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

> `access_token`, `refresh_token`은 저장 전 AES-256-GCM으로 암호화됨.

---

### 3.5 `contents` — 콘텐츠

콘텐츠 기획부터 게시까지 전 주기를 관리하는 핵심 테이블.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `client_id` | `uuid` | NO | — | FK → `clients.id` |
| `title` | `varchar(500)` | NO | — | 콘텐츠 제목 |
| `body` | `text` | YES | — | 본문 텍스트 (캡션/스크립트) |
| `content_type` | `content_type` | NO | — | 유형 (`feed`/`reel`/`story`/`short`/`card_news`) |
| `status` | `content_status` | NO | `'draft'` | 워크플로 상태 |
| `media_urls` | `jsonb` | YES | — | 첨부 미디어 URL 목록 JSON |
| `hashtags` | `text[]` | YES | — | 해시태그 배열 |
| `target_platforms` | `text[]` | NO | — | 게시 대상 플랫폼 배열 |
| `scheduled_at` | `timestamptz` | YES | — | 예약 게시 시각 |
| `published_at` | `timestamptz` | YES | — | 실제 게시 완료 시각 |
| `approved_at` | `timestamptz` | YES | — | 최종 승인 시각 |
| `approved_by` | `uuid` | YES | — | FK → `users.id` (승인자) |
| `ai_metadata` | `jsonb` | YES | — | AI 생성 메타데이터 (품질 점수, 제안 등) JSON |
| `created_by` | `uuid` | NO | — | FK → `users.id` (작성자) |
| `created_at` | `timestamptz` | YES | `now()` | 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

**콘텐츠 상태 흐름**:
```
draft → review → client_review → approved → published
          ↑
       rejected (→ draft 복귀 가능)
```

---

### 3.6 `content_approvals` — 콘텐츠 승인 이력

콘텐츠의 모든 상태 변경(승인·반려·검토) 이력을 시계열로 기록.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `content_id` | `uuid` | NO | — | FK → `contents.id` |
| `from_status` | `content_status` | NO | — | 변경 전 상태 |
| `to_status` | `content_status` | NO | — | 변경 후 상태 |
| `reviewer_id` | `uuid` | NO | — | FK → `users.id` (검토자) |
| `comment` | `text` | YES | — | 승인/반려 사유 코멘트 |
| `is_urgent` | `boolean` | YES | `false` | 긴급 처리 요청 여부 |
| `created_at` | `timestamptz` | YES | `now()` | 이력 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

---

### 3.7 `publishing_logs` — 게시 로그

Celery 비동기 작업으로 실행된 플랫폼 게시 작업의 상태 및 결과.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `content_id` | `uuid` | NO | — | FK → `contents.id` |
| `platform_account_id` | `uuid` | NO | — | FK → `platform_accounts.id` |
| `status` | `publishing_status` | NO | — | 게시 상태 (`pending`/`publishing`/`success`/`failed`/`cancelled`) |
| `platform_post_id` | `varchar(200)` | YES | — | 게시 성공 시 플랫폼에서 반환한 포스트 ID |
| `platform_post_url` | `varchar(500)` | YES | — | 게시된 포스트 URL |
| `error_message` | `text` | YES | — | 게시 실패 시 오류 메시지 |
| `retry_count` | `integer` | YES | `0` | 재시도 횟수 |
| `scheduled_at` | `timestamptz` | YES | — | 예약 게시 시각 |
| `published_at` | `timestamptz` | YES | — | 실제 게시 완료 시각 |
| `celery_task_id` | `varchar(200)` | YES | — | Celery 작업 ID (추적용) |
| `created_at` | `timestamptz` | YES | `now()` | 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

---

### 3.8 `comments_inbox` — 댓글 수신함

SNS 플랫폼에서 수집된 댓글을 통합 관리. AI 감성 분석 결과 및 응대 현황 포함.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `platform_account_id` | `uuid` | NO | — | FK → `platform_accounts.id` |
| `content_id` | `uuid` | YES | — | FK → `contents.id` (연결된 콘텐츠, 없을 수 있음) |
| `platform_comment_id` | `varchar(200)` | NO | — | 플랫폼의 원본 댓글 ID |
| `parent_comment_id` | `uuid` | YES | — | FK → `comments_inbox.id` (대댓글인 경우 부모 댓글) |
| `author_name` | `varchar(200)` | NO | — | 댓글 작성자 닉네임 |
| `author_profile_url` | `varchar(500)` | YES | — | 작성자 프로필 URL |
| `message` | `text` | NO | — | 댓글 원문 |
| `sentiment` | `sentiment` | YES | — | AI 감성 분석 결과 (`positive`/`neutral`/`negative`/`crisis`) |
| `sentiment_score` | `float8` | YES | — | 감성 점수 (0.0 ~ 1.0, 낮을수록 부정) |
| `status` | `comment_status` | NO | `'pending'` | 처리 상태 (`pending`/`replied`/`hidden`/`flagged`) |
| `ai_reply_draft` | `text` | YES | — | AI가 생성한 답변 초안 |
| `replied_at` | `timestamptz` | YES | — | 실제 답변 전송 시각 |
| `replied_by` | `uuid` | YES | — | FK → `users.id` (답변한 운영자) |
| `commented_at` | `timestamptz` | NO | — | 원본 댓글 작성 시각 (플랫폼 기준) |
| `created_at` | `timestamptz` | YES | `now()` | DB 수집 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

---

### 3.9 `analytics_snapshots` — 분석 스냅샷

플랫폼 API에서 수집한 성과 지표를 일별로 스냅샷 저장. 대시보드 차트 데이터 소스.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `platform_account_id` | `uuid` | NO | — | FK → `platform_accounts.id` |
| `snapshot_date` | `date` | NO | — | 스냅샷 날짜 |
| `metrics` | `jsonb` | NO | — | 지표 JSON (reach, impressions, engagement, followers 등) |
| `content_id` | `uuid` | YES | — | FK → `contents.id` (콘텐츠별 지표인 경우) |
| `created_at` | `timestamptz` | YES | `now()` | 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

**제약**: `UNIQUE(platform_account_id, snapshot_date, content_id)` — 중복 수집 방지

**`metrics` JSONB 구조 예시**:
```json
{
  "reach": 12500,
  "impressions": 18300,
  "engagement": 847,
  "engagement_rate": 6.78,
  "followers": 25400,
  "likes": 620,
  "comments": 45,
  "shares": 182
}
```

---

### 3.10 `notifications` — 알림

사용자에게 전달되는 인앱 알림. WebSocket으로 실시간 푸시.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `user_id` | `uuid` | NO | — | FK → `users.id` (수신자) |
| `type` | `notification_type` | NO | — | 알림 유형 |
| `title` | `varchar(200)` | NO | — | 알림 제목 |
| `message` | `text` | NO | — | 알림 내용 |
| `reference_type` | `varchar(50)` | YES | — | 연결 엔티티 유형 (예: `content`, `comment`) |
| `reference_id` | `uuid` | YES | — | 연결 엔티티 ID |
| `is_read` | `boolean` | YES | `false` | 읽음 여부 |
| `read_at` | `timestamptz` | YES | — | 읽은 시각 |
| `priority` | `notification_priority` | YES | `'normal'` | 우선순위 |
| `created_at` | `timestamptz` | YES | `now()` | 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

---

### 3.11 `audit_logs` — 감사 로그

모든 생성·수정·삭제·승인·게시·로그인 이벤트를 불변 기록으로 저장.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `user_id` | `uuid` | NO | — | FK → `users.id` (행위 주체) |
| `action` | `audit_action` | NO | — | 수행 액션 |
| `entity_type` | `varchar(50)` | NO | — | 대상 엔티티 타입 (예: `content`, `user`) |
| `entity_id` | `uuid` | YES | — | 대상 엔티티 ID |
| `changes` | `jsonb` | YES | — | 변경 전후 값 JSON `{"before": {}, "after": {}}` |
| `ip_address` | `varchar(45)` | YES | — | 요청 IP (IPv4/IPv6 지원) |
| `user_agent` | `varchar(500)` | YES | — | 요청 브라우저 User-Agent |
| `created_at` | `timestamptz` | YES | `now()` | 이벤트 발생 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

---

### 3.12 `faq_guidelines` — FAQ / 가이드라인

RAG(검색 증강 생성) 기반 AI 댓글 응대를 위한 클라이언트별 지식 베이스.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `client_id` | `uuid` | NO | — | FK → `clients.id` |
| `category` | `faq_category` | NO | — | 카테고리 (`faq`/`tone_manner`/`crisis_scenario`/`template`) |
| `title` | `varchar(300)` | NO | — | 항목 제목 |
| `content` | `text` | NO | — | 내용 (FAQ 답변, 가이드라인 본문) |
| `tags` | `text[]` | YES | — | 검색용 태그 배열 |
| `is_active` | `boolean` | YES | `true` | 활성 여부 |
| `priority` | `integer` | YES | `0` | 검색 우선순위 (높을수록 우선) |
| `created_at` | `timestamptz` | YES | `now()` | 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

> 등록 시 자동으로 `vector_embeddings`에 임베딩 생성 (RAG 파이프라인).

---

### 3.13 `filter_rules` — 필터 규칙

댓글 자동 필터링 규칙. 키워드·패턴·사용자 차단 등 설정.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `client_id` | `uuid` | NO | — | FK → `clients.id` |
| `rule_type` | `rule_type` | NO | — | 규칙 유형 (`keyword`/`pattern`/`user_block`) |
| `value` | `varchar(500)` | NO | — | 규칙 값 (키워드 문자열 또는 정규식 패턴) |
| `action` | `filter_action` | NO | — | 적용 액션 (`hide`/`flag`/`delete`) |
| `is_active` | `boolean` | YES | `true` | 활성 여부 |
| `created_at` | `timestamptz` | YES | `now()` | 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

---

### 3.14 `vector_embeddings` — 벡터 임베딩

pgvector를 활용한 RAG 파이프라인의 벡터 저장소. FAQ·가이드라인 텍스트를 청크 단위로 임베딩.

| 컬럼명 | 타입 | NULL | 기본값 | 설명 |
|--------|------|------|--------|------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `source_type` | `varchar(50)` | NO | — | 원본 엔티티 타입 (예: `faq_guideline`) |
| `source_id` | `uuid` | NO | — | 원본 엔티티 ID |
| `chunk_index` | `integer` | NO | — | 텍스트 청크 순서 번호 |
| `chunk_text` | `text` | NO | — | 임베딩된 텍스트 청크 원문 |
| `metadata` | `jsonb` | YES | — | 추가 메타데이터 JSON (client_id, category 등) |
| `embedding` | `vector(1536)` | NO | — | OpenAI text-embedding-3-small 1536차원 벡터 |
| `created_at` | `timestamptz` | YES | `now()` | 생성 시각 |
| `updated_at` | `timestamptz` | YES | `now()` | 수정 시각 |

> IVFFlat 인덱스(`lists=100`, `vector_cosine_ops`)로 코사인 유사도 ANN 검색 최적화.

---

## 4. 인덱스 목록

| 인덱스명 | 테이블 | 컬럼 | 유형 | 목적 |
|----------|--------|------|------|------|
| `users_email_key` | `users` | `email` | UNIQUE B-tree | 이메일 중복 방지, 로그인 조회 |
| `uq_user_client` | `user_client_assignments` | `(user_id, client_id)` | UNIQUE B-tree | 중복 배정 방지 |
| `idx_uca_user` | `user_client_assignments` | `user_id` | B-tree | 사용자별 담당 클라이언트 조회 |
| `idx_uca_client` | `user_client_assignments` | `client_id` | B-tree | 클라이언트별 담당자 조회 |
| `idx_contents_client_status` | `contents` | `(client_id, status)` | B-tree | 칸반보드 상태별 콘텐츠 조회 |
| `idx_contents_calendar` | `contents` | `(client_id, scheduled_at)` | B-tree | 콘텐츠 캘린더 날짜 범위 조회 |
| `idx_contents_scheduled` | `contents` | `scheduled_at` WHERE `status='approved'` | Partial B-tree | Celery 예약 게시 작업 조회 |
| `idx_approval_content` | `content_approvals` | `(content_id, created_at)` | B-tree | 콘텐츠 승인 이력 시계열 조회 |
| `idx_publog_content` | `publishing_logs` | `(content_id, status)` | B-tree | 게시 로그 상태 조회 |
| `idx_comments_account_status` | `comments_inbox` | `(platform_account_id, status)` | B-tree | 계정별 댓글 처리 현황 조회 |
| `idx_comments_sentiment_negative` | `comments_inbox` | `sentiment` WHERE `='negative'` | Partial B-tree | 부정 댓글 필터링 |
| `idx_comments_sentiment_crisis` | `comments_inbox` | `sentiment` WHERE `='crisis'` | Partial B-tree | 위기 댓글 즉시 탐지 |
| `idx_analytics_account_date` | `analytics_snapshots` | `(platform_account_id, snapshot_date)` | B-tree | 날짜 범위 성과 조회 |
| `uq_analytics_snapshot` | `analytics_snapshots` | `(platform_account_id, snapshot_date, content_id)` | UNIQUE B-tree | 중복 수집 방지 |
| `idx_notif_user_unread` | `notifications` | `(user_id, is_read)` WHERE `is_read=false` | Partial B-tree | 미읽음 알림 배지 카운트 |
| `idx_filter_client_active` | `filter_rules` | `client_id` WHERE `is_active=true` | Partial B-tree | 활성 필터 규칙 적용 |
| `idx_audit_entity` | `audit_logs` | `(entity_type, entity_id, created_at)` | B-tree | 엔티티별 감사 이력 조회 |
| `idx_vector_ivfflat` | `vector_embeddings` | `embedding` | **IVFFlat** (cosine) | ANN 벡터 유사도 검색 |

---

## 5. 외래키 관계

```
users ──┬──< clients (manager_id)
        ├──< user_client_assignments (user_id)
        ├──< contents (created_by, approved_by)
        ├──< content_approvals (reviewer_id)
        ├──< comments_inbox (replied_by)
        ├──< notifications (user_id)
        └──< audit_logs (user_id)

clients ──┬──< user_client_assignments (client_id)
          ├──< platform_accounts (client_id)
          ├──< contents (client_id)
          ├──< faq_guidelines (client_id)
          └──< filter_rules (client_id)

platform_accounts ──┬──< comments_inbox (platform_account_id)
                    ├──< analytics_snapshots (platform_account_id)
                    └──< publishing_logs (platform_account_id)

contents ──┬──< content_approvals (content_id)
           ├──< publishing_logs (content_id)
           ├──< comments_inbox (content_id)
           └──< analytics_snapshots (content_id)

comments_inbox ──< comments_inbox (parent_comment_id)  ← 자기참조 (대댓글)

faq_guidelines ──> vector_embeddings (source_id, source_type='faq_guideline')
```

---

## 6. ERD 요약

```
┌──────────┐      ┌───────────────────────┐      ┌──────────┐
│  users   │─────<│ user_client_assignments│>─────│ clients  │
└──────────┘      └───────────────────────┘      └──────────┘
     │                                                 │
     │                                    ┌────────────┤
     │                                    │            │
     ▼                                    ▼            ▼
┌──────────┐      ┌──────────────────┐  ┌──────────────────┐
│ contents │─────<│ content_approvals│  │ platform_accounts│
└──────────┘      └──────────────────┘  └──────────────────┘
     │                                         │
     ├─────────────────────────────────────────┤
     │                    │                    │
     ▼                    ▼                    ▼
┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐
│publishing_logs│  │comments_inbox │  │ analytics_snapshots  │
└──────────────┘  └───────────────┘  └──────────────────────┘

┌────────────────┐      ┌───────────────────┐
│ faq_guidelines │─────>│ vector_embeddings │
└────────────────┘      └───────────────────┘

┌──────────────┐  ┌──────────────┐  ┌────────────┐
│ filter_rules │  │ notifications│  │ audit_logs │
└──────────────┘  └──────────────┘  └────────────┘
```
