# 05. 외부 시스템 연동

## 1. SNS 플랫폼 API

### Meta Graph API v19 (Instagram + Facebook)

| 기능 | API | 연동 범위 |
|------|-----|---------|
| **Instagram** | Meta Graph API v19 | 피드/릴스/스토리 게시, 댓글 조회/응답, 인사이트 수집 |
| **Facebook** | Meta Graph API v19 | 포스트/릴스 게시, 댓글 관리, 페이지 인사이트 수집 |

```python
# integrations/meta/client.py
class MetaGraphClient:
    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, access_token: str):
        self.access_token = access_token  # AES-256 복호화된 토큰
        self.session = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={"Authorization": f"Bearer {access_token}"}
        )

    # 게시
    async def publish_feed(self, page_id: str, message: str, media_url: str | None):
        ...

    # 댓글 조회
    async def get_comments(self, media_id: str, after: str | None = None):
        ...

    # 인사이트 수집
    async def get_insights(self, object_id: str, metrics: list[str], period: str):
        ...
```

### YouTube Data API v3

| 기능 | 연동 범위 |
|------|---------|
| **YouTube** | 영상/쇼츠 업로드, 댓글 관리, 채널 통계 수집 |

```python
# integrations/youtube/client.py
class YouTubeClient:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    # 영상 업로드 (resumable upload)
    async def upload_video(self, file_path: str, metadata: dict):
        ...

    # 댓글 조회
    async def get_comments(self, video_id: str, page_token: str | None = None):
        ...

    # 채널 통계
    async def get_channel_stats(self, channel_id: str):
        ...
```

### OAuth 토큰 관리 공통

```python
# 각 플랫폼 계정의 토큰은 platform_accounts 테이블에 AES-256-GCM 암호화 저장
# 암호화/복호화 구현 상세: docs/04-auth-security.md Section 3 (AES-256-GCM 유틸) 참조
# Celery Beat이 매시간 토큰 만료 임박 계정을 스캔하여 자동 갱신
# Celery 작업 정의 상세: docs/06-async-realtime.md Section 1 (데이터 수집 작업) 참조

async def refresh_platform_token(account: PlatformAccount) -> bool:
    """Refresh Token으로 새 Access Token 획득 후 DB 업데이트"""
    if account.platform in ("instagram", "facebook"):
        new_token = await meta_client.exchange_token(account.refresh_token)
    elif account.platform == "youtube":
        new_token = await youtube_client.refresh_token(account.refresh_token)
    account.access_token = encryptor.encrypt(new_token.access_token)
    account.token_expires_at = new_token.expires_at
    await db.commit()
```

---

## 2. AI 서비스 연동

### AI 기능 5종 매핑

| 기능 | 기술 | 구현 방식 |
|------|------|---------|
| **카피/캡션 생성** | Claude / GPT-4o API | 브랜드 가이드라인 System Prompt, 복수 초안 |
| **감성 분석** | Fine-tuned KcELECTRA | 한국어 특화 4분류 (positive/neutral/negative/crisis) |
| **RAG 응대** | LLM + pgvector | FAQ/매뉴얼 벡터 검색 → LLM 초안 생성 |
| **AI 질의 챗봇** | Claude/GPT + Text-to-SQL | 자연어 → SQL → DB 조회 → 자연어 응답 |
| **최적 시간 추천** | Prophet / LightGBM | 과거 참여율 기반 시계열 분석 |

### LLM 통합 클라이언트

```python
# integrations/ai/llm_client.py
class LLMClient:
    """Claude/GPT 통합 클라이언트 — 프로바이더 추상화"""

    def __init__(self, provider: str = "claude"):
        if provider == "claude":
            self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = "claude-sonnet-4-20250514"
        elif provider == "openai":
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "gpt-4o"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """텍스트 생성 (카피, 응대 초안 등)"""
        ...

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        """SSE 스트리밍 (AI 챗봇)"""
        ...
```

### RAG 파이프라인

```python
# integrations/ai/rag.py
class RAGPipeline:
    """FAQ/가이드라인 기반 응대 초안 생성"""

    async def generate_reply_draft(
        self, comment: Comment, client_id: UUID
    ) -> str:
        # 1. 댓글 텍스트를 임베딩으로 변환
        query_embedding = await self.embed(comment.message)

        # 2. pgvector에서 유사 FAQ/가이드라인 검색 (client_id 필터)
        similar_docs = await self.vector_search(
            query_embedding,
            filter={"client_id": str(client_id)},
            top_k=5
        )

        # 3. 검색된 문서를 컨텍스트로 LLM에 전달
        context = "\n".join([doc.chunk_text for doc in similar_docs])
        system_prompt = f"""
        당신은 {client.name}의 SNS 운영 담당자입니다.
        다음 가이드라인을 참고하여 댓글에 대한 응대 초안을 작성하세요.
        
        [가이드라인]
        {context}
        
        [톤앤매너]
        {client.brand_guidelines.get("tone", "친절하고 전문적인")}
        """
        return await self.llm.generate(system_prompt, comment.message)
```

### 벡터 임베딩 생성

```python
# integrations/ai/embeddings.py
class EmbeddingService:
    """텍스트 → 벡터 임베딩 (pgvector 저장)"""

    async def create_embeddings(self, source_type: str, source_id: UUID, text: str):
        # 1. 텍스트를 청크로 분할 (500자 단위, 100자 오버랩)
        chunks = self.chunk_text(text, chunk_size=500, overlap=100)

        # 2. 각 청크를 벡터로 변환
        for i, chunk in enumerate(chunks):
            embedding = await self.embed(chunk)  # settings.EMBEDDING_MODEL (기본: text-embedding-3-small)
            await db.execute(
                insert(VectorEmbedding).values(
                    source_type=source_type,
                    source_id=source_id,
                    chunk_index=i,
                    chunk_text=chunk,
                    embedding=embedding,
                    metadata={"client_id": str(client_id)}
                )
            )
```

---

## 3. 외부 API 공통 연동 전략

모든 외부 API 연동에 공통 적용하는 안정성/회복탄력성 패턴:

### Rate Limiting 관리

```python
# Redis 카운터로 플랫폼별 API 호출 쿼터 추적
async def check_rate_limit(platform: str) -> bool:
    key = f"api_quota:{platform}:{datetime.now().strftime('%Y%m%d%H')}"
    current = await redis.incr(key)
    await redis.expire(key, 3600)
    limit = PLATFORM_LIMITS[platform]  # Meta: 200/hr, YouTube: 10000/day
    if current >= limit * 0.8:
        await notify_admin(f"{platform} API 쿼터 80% 도달")
    return current < limit
```

### Circuit Breaker

```
상태: CLOSED → OPEN → HALF_OPEN → CLOSED
- CLOSED: 정상 호출
- 연속 5회 실패 → OPEN (30초 차단)
- 30초 후 → HALF_OPEN (1건 시도)
- 성공 → CLOSED / 실패 → OPEN 복귀
```

### Retry with Exponential Backoff

```python
# 429 (Rate Limited) 또는 5xx 응답 시
RETRY_CONFIG = {
    "max_retries": 3,
    "backoff_base": 1,      # 1초 → 2초 → 4초
    "backoff_factor": 2,
    "retryable_status": [429, 500, 502, 503, 504],
}
```

### 토큰 자동 갱신

```
- Celery Beat: 1시간 주기로 만료 임박 토큰 스캔
- 조건: token_expires_at < now() + 24시간
- 동작: Refresh Token으로 새 Access Token 획득
- 실패 시: 알림 발송 (재연동 필요)
```

> Celery Beat 스케줄 및 작업 정의는 `docs/06-async-realtime.md` Section 1 참조.

### 응답 캐싱

| 데이터 | Redis TTL | Key 패턴 |
|--------|----------|---------|
| 인사이트 데이터 | 1시간 | `cache:analytics:{account_id}:{date}` |
| 프로필/계정 정보 | 24시간 | `cache:profile:{account_id}` |
| API 일반 응답 | 5분 | `cache:api:{request_hash}` |
