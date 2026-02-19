# 06. 비동기 처리 및 실시간 통신

## 1. Celery Worker 구성

### 아키텍처

```
Redis Broker → Celery Worker(s) → 결과 저장 / WebSocket 알림
                 │
                 ├── critical 큐: SNS 게시 (예약 시간 엄수)
                 ├── high 큐:     AI 분석, 감성 분석
                 ├── medium 큐:   데이터 수집, 토큰 갱신
                 └── low 큐:      리포트, 벡터 임베딩
```

### Celery 설정

```python
# tasks/celery_app.py
from celery import Celery
from celery.schedules import crontab

celery_app = Celery("sns_solution", broker=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    task_routes={
        "app.tasks.publishing_tasks.*": {"queue": "critical"},
        "app.tasks.ai_tasks.*":         {"queue": "high"},
        "app.tasks.data_collection_tasks.*": {"queue": "medium"},
        "app.tasks.report_tasks.*":     {"queue": "low"},
    },
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Celery Beat 스케줄
celery_app.conf.beat_schedule = {
    # 예약 게시 스캔 (1분마다)
    "scan-scheduled-posts": {
        "task": "app.tasks.publishing_tasks.scan_scheduled_posts",
        "schedule": 60.0,
    },
    # 댓글 동기화 (5분마다)
    "sync-comments": {
        "task": "app.tasks.data_collection_tasks.sync_comments",
        "schedule": 300.0,
    },
    # KPI 수집 (1시간마다)
    "collect-analytics": {
        "task": "app.tasks.data_collection_tasks.collect_analytics",
        "schedule": 3600.0,
    },
    # 토큰 만료 스캔 (1시간마다)
    "refresh-expiring-tokens": {
        "task": "app.tasks.data_collection_tasks.refresh_expiring_tokens",
        "schedule": 3600.0,
    },
    # 일간 리포트 (매일 08:00)
    "daily-report": {
        "task": "app.tasks.report_tasks.generate_daily_report",
        "schedule": crontab(hour=8, minute=0),
    },
}
```

### 작업 유형 상세 (5종)

#### 1) SNS 게시 (CRITICAL)

```python
# tasks/publishing_tasks.py
@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def publish_to_platform(self, content_id: str, platform_account_id: str):
    """
    1. DB에서 콘텐츠 + 계정 정보 로드
    2. 플랫폼 API 호출 (Meta/YouTube)
    3. publishing_logs 업데이트 (success/failed)
    4. 성공 시: contents.published_at 기록
    5. WebSocket: 게시 결과 실시간 알림
    6. 실패 시: retry + publishing_logs.retry_count++
    """

@celery_app.task
def scan_scheduled_posts():
    """1분마다 실행: scheduled_at <= now() 인 approved 콘텐츠 발견 시 publish_to_platform 발행"""
```

#### 2) AI 분석 (HIGH)

```python
# tasks/ai_tasks.py
@celery_app.task
def analyze_sentiment(comment_id: str):
    """KcELECTRA로 감성 분석 → comments_inbox.sentiment/score 업데이트"""

@celery_app.task
def generate_copy(request_data: dict) -> dict:
    """LLM으로 카피 생성 → 결과 반환"""

@celery_app.task
def generate_reply_draft(comment_id: str, client_id: str):
    """RAG 파이프라인으로 응대 초안 생성 → comments_inbox.ai_reply_draft 업데이트"""

@celery_app.task
def generate_metadata(content_id: str):
    """LLM/VLM으로 해시태그, 캡션, 대체텍스트 생성 → contents.ai_metadata 업데이트"""
```

#### 3) 데이터 수집 (MEDIUM)

```python
# tasks/data_collection_tasks.py
@celery_app.task
def sync_comments():
    """
    5분마다: 모든 활성 platform_accounts의 최신 댓글 수집
    → comments_inbox에 upsert (platform_comment_id 기준)
    → 새 댓글 발견 시 감성 분석 태스크 체이닝
    → WebSocket: 새 댓글 실시간 푸시
    """

@celery_app.task
def collect_analytics():
    """
    1시간마다: 인사이트 API 호출
    → analytics_snapshots에 일별 KPI 저장
    → Redis 캐시 갱신
    """

@celery_app.task
def refresh_expiring_tokens():
    """
    1시간마다: token_expires_at < now() + 24h 인 계정 스캔
    → OAuth Refresh Token으로 새 Access Token 발급
    → 실패 시: 관리자 알림 (재연동 필요)
    """
```

#### 4) 리포트 생성 (LOW)

```python
# tasks/report_tasks.py
@celery_app.task
def generate_ai_insight_report(client_id: str, period: str):
    """
    LLM으로 성과 분석 리포트 생성
    → 3줄 요약 + 상세 분석 + 전략 추천
    → PDF 생성 → S3 업로드
    → 알림: 리포트 준비 완료
    """

@celery_app.task
def generate_daily_report():
    """매일 08:00: 전 클라이언트 일간 요약 자동 생성"""

@celery_app.task
def send_newsletter(client_id: str, report_url: str):
    """이메일 자동 발송"""
```

#### 5) 벡터 임베딩 (LOW)

```python
@celery_app.task
def update_embeddings(source_type: str, source_id: str):
    """
    FAQ/가이드라인 등록/수정 시:
    1. 기존 벡터 삭제 (source_type + source_id)
    2. 텍스트 청크 분할 (500자, 100자 오버랩)
    3. 임베딩 생성 → vector_embeddings 저장
    """
```

---

## 2. 실시간 통신 (WebSocket)

### WebSocket 엔드포인트

> WebSocket 인증 정책(JWT 검증, 토큰 만료 처리, close code)은 `docs/04-auth-security.md` Section 1 (WebSocket 인증) 참조.

```python
# api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
import json

class ConnectionManager:
    """사용자별 WebSocket 연결 관리"""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}  # user_id → [ws...]

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)
        await redis.set(f"online:{user_id}", "1", ex=300)  # 5분 TTL

    async def disconnect(self, websocket: WebSocket, user_id: str):
        self.active_connections[user_id].remove(websocket)
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]
            await redis.delete(f"online:{user_id}")

    async def send_to_user(self, user_id: str, message: dict):
        for ws in self.active_connections.get(user_id, []):
            await ws.send_json(message)

    async def broadcast_to_role(self, role: str, message: dict):
        # Redis Pub/Sub으로 다른 워커에도 브로드캐스트
        await redis.publish(f"pubsub:role:{role}", json.dumps(message))

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # 1. JWT 검증
    user = await verify_ws_token(token)
    if not user:
        await websocket.close(code=4001)  # 토큰 만료/무효
        return

    # 2. 연결 수립
    await manager.connect(websocket, str(user.id))

    try:
        while True:
            # 90초 무응답 타임아웃 (클라이언트는 30초마다 ping 전송)
            data = await asyncio.wait_for(websocket.receive_text(), timeout=90)
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                await redis.set(f"online:{user.id}", "1", ex=300)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, str(user.id))
```

### WebSocket 이벤트 유형 (6종)

| 이벤트 | 발신 트리거 | 수신 대상 | 페이로드 |
|-------|-----------|---------|---------|
| **crisis_alert** | 부정 감성 급증 (AI 감지) | 해당 클라이언트 담당자 전원 | `{type, client_id, severity, message, comment_ids}` |
| **publish_result** | 게시 성공/실패 (Celery 완료) | 콘텐츠 작성자 | `{type, content_id, platform, status, post_url?, error?}` |
| **approval_request** | 콘텐츠 상태 변경 (검토 요청) | 검수자 (manager/client) | `{type, content_id, title, from_status, to_status, requester}` |
| **new_comment** | 새 댓글 동기화 (Celery) | 해당 계정 운영자 | `{type, comment_id, platform, author, message, sentiment}` |
| **notification** | 모든 알림 이벤트 | 대상 사용자 | `{type, notification_id, title, message, priority, reference}` |
| **chat_stream** | AI 챗봇 응답 | 요청 사용자 | `{type, chunk, conversation_id, done}` — SSE 방식 |

### Redis Pub/Sub 연동

```python
# WebSocket 서버가 여러 인스턴스일 때 Redis Pub/Sub으로 동기화
async def redis_subscriber():
    """백그라운드: Redis 채널 구독 → WebSocket 전달"""
    pubsub = redis.pubsub()
    await pubsub.subscribe("pubsub:notifications")
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            user_id = data.get("user_id")
            if user_id:
                await manager.send_to_user(user_id, data)
```

### 알림 센터 동기화

```python
# 알림 발생 시 처리 순서:
async def send_notification(user_id: str, notification: dict):
    # 1. DB 저장 (notifications 테이블)
    await db.execute(insert(Notification).values(**notification))

    # 2. Redis unread 카운터 증가
    await redis.incr(f"notif:unread:{user_id}")

    # 3. WebSocket 푸시
    await manager.send_to_user(user_id, {
        "type": "notification",
        **notification
    })

    # 4. Redis Pub/Sub (다중 인스턴스 동기화)
    await redis.publish("pubsub:notifications", json.dumps({
        "user_id": user_id,
        "type": "notification",
        **notification
    }))
```

### 프론트엔드 WebSocket Hook

```typescript
// hooks/useWebSocket.ts
export const useWebSocket = () => {
  const { token } = useAuthStore();
  const { incrementUnread, addNotification } = useNotificationStore();

  useEffect(() => {
    if (!token) return;

    const ws = new WebSocket(`${WS_URL}/ws?token=${token}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case "notification":
          addNotification(data);
          incrementUnread();
          toast({ title: data.title, description: data.message });
          break;
        case "crisis_alert":
          // 긴급 알림 UI (빨간색 배너)
          showCrisisAlert(data);
          break;
        case "publish_result":
          queryClient.invalidateQueries({ queryKey: ["publishing"] });
          break;
        case "new_comment":
          queryClient.invalidateQueries({ queryKey: ["community", "inbox"] });
          break;
      }
    };

    // 30초 하트비트
    const heartbeat = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000);

    // 자동 재연결 (지수 백오프)
    ws.onclose = (event) => {
      if (event.code === 4001) {
        // 토큰 만료: 갱신 후 재연결
        refreshToken().then(() => reconnect());
      } else {
        setTimeout(reconnect, backoff(retryCount));
      }
    };

    return () => { clearInterval(heartbeat); ws.close(); };
  }, [token]);
};
```
