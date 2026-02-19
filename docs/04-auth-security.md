# 04. 인증 및 보안

## 1. 인증 흐름

### JWT 이중 토큰 구조

| 토큰 | 알고리즘 | 만료 | 저장 위치 | 페이로드 |
|------|---------|------|---------|---------|
| Access Token | HS256 | 30분 | 메모리 (Zustand) | user_id, role, client_ids |
| Refresh Token | 랜덤 UUID | 7일 | Redis (`session:{user_id}`) | user_id 매핑 |

### 토큰 발급 플로우

```
1. POST /auth/login (email + password)
2. 서버: bcrypt 검증 → JWT Access 생성 + UUID Refresh 생성
3. Redis: session:{user_id} = {refresh_token, issued_at, user_agent}
4. 응답: { access_token, refresh_token, expires_in: 1800 }
```

### 토큰 갱신 (Token Rotation)

```
1. POST /auth/refresh (refresh_token)
2. 서버: Redis에서 refresh_token 검증
3. 기존 Refresh 토큰 무효화 (삭제)
4. 새 Access + 새 Refresh 발급
5. 응답: 새 토큰 쌍
```

- Refresh 토큰 재사용 감지: 이미 사용된 토큰이 다시 전달되면 해당 user_id의 모든 세션 무효화 (탈취 의심)

### SNS OAuth 플로우

```
1. 프론트엔드: 플랫폼 OAuth URL로 리다이렉트
2. 사용자: 플랫폼에서 권한 승인
3. 콜백: POST /auth/oauth/{platform}/callback (authorization_code)
4. 서버: code → access_token/refresh_token 교환
5. 토큰 AES-256-GCM 암호화 → platform_accounts 테이블 저장
```

### WebSocket 인증

```
1. 클라이언트: ws://host/ws?token={access_token}
2. 서버: query parameter에서 JWT 검증
3. 검증 성공: 연결 수립, Redis online:{user_id} 등록
4. 토큰 만료: close code 4001 전송
5. 클라이언트: 토큰 갱신 후 재연결 (자동)
6. 하트비트: 30초 주기 ping/pong, 90초 무응답 시 연결 종료
```

> WebSocket 구현 상세(ConnectionManager, 이벤트 유형, Redis Pub/Sub)는 `docs/06-async-realtime.md` Section 2 참조.

---

## 2. RBAC 권한 매트릭스

### 역할별 기능 접근 권한

| 기능 | admin | manager | operator | client |
|------|-------|---------|----------|--------|
| 콘텐츠 작성 | ✅ | ✅ | ✅ | ❌ |
| 콘텐츠 승인 | ✅ | ✅ | ❌ | ✅ (본인 계정) |
| 게시 실행 | ✅ | ✅ | ✅ | ❌ |
| 성과 조회 | ✅ | ✅ | ✅ | ✅ (본인 계정) |
| 사용자 관리 | ✅ | ❌ | ❌ | ❌ |
| 클라이언트 관리 | ✅ | ✅ | ◑ (배정 계정) | ❌ |
| AI 도구 | ✅ | ✅ | ✅ | ✅ (AI 질의만) |
| 설정 변경 | ✅ | ✅ (제한) | ❌ | ❌ |
| 알림 관리 | ✅ | ✅ | ✅ | ✅ (본인) |
| 감사 로그 조회 | ✅ | ✅ | ❌ | ❌ |

### FastAPI Dependency 구현

```python
# dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """JWT에서 현재 사용자 추출"""
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user = await db.get(User, payload["user_id"])
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid or inactive user")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*roles: str):
    """역할 기반 접근 제어 데코레이터"""
    async def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return Depends(dependency)

# 사용 예시
@router.post("/users")
async def create_user(
    data: UserCreate,
    admin: User = require_role("admin"),          # admin 전용
    db: AsyncSession = Depends(get_db)
):
    ...

@router.get("/contents")
async def list_contents(
    user: User = Depends(get_current_user),       # 인증만 필요
    db: AsyncSession = Depends(get_db)
):
    # client 역할이면 본인 계정 콘텐츠만 필터링
    if user.role == "client":
        query = query.filter(Content.client_id.in_(user.client_ids))
    ...
```

---

## 3. 보안 적용 사항 (8항목)

| # | 항목 | 구현 방식 |
|---|------|---------|
| 1 | **HTTPS 전용** | TLS 1.3, Nginx SSL 종료, HSTS 헤더 |
| 2 | **CORS** | 화이트리스트 도메인 (개발: localhost, 프로덕션: 지정 도메인) |
| 3 | **SQL Injection 방지** | SQLAlchemy ORM 파라미터 바인딩 전용, 직접 SQL 금지 |
| 4 | **XSS 방지** | React 자동 이스케이프 + DOMPurify (TipTap 에디터 출력) |
| 5 | **CSRF** | SameSite=Strict 쿠키 + CSRF 토큰 |
| 6 | **API Rate Limiting** | Redis 기반, 사용자/엔드포인트별 제한 |
| 7 | **민감 데이터 암호화** | OAuth 토큰 AES-256-GCM 저장 |
| 8 | **감사 로그** | 모든 CUD + 승인/게시 → audit_logs 자동 기록 |

### CORS 설정

```python
# middleware/cors.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS.split(","),  # .env에서 로드
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Rate Limiting

```python
# middleware/rate_limiter.py — Redis 기반
async def rate_limit(user_id: str, endpoint: str, limit: int = 60, window: int = 60):
    key = f"ratelimit:{user_id}:{endpoint}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window)
    if current > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

### AES-256-GCM 암호화 유틸

```python
# utils/encryption.py
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os, base64

class TokenEncryptor:
    def __init__(self, key: bytes):  # settings.ENCRYPTION_KEY (32 bytes)
        self.aesgcm = AESGCM(key)

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode()

    def decrypt(self, token: str) -> str:
        data = base64.b64decode(token)
        nonce, ciphertext = data[:12], data[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None).decode()
```

---

## 4. 파일 업로드 보안

| 항목 | 정책 |
|------|------|
| **허용 형식** | 이미지: jpg, png, gif, webp / 영상: mp4, mov, avi / 문서: pdf |
| **크기 제한** | 이미지 20MB, 영상 500MB, 문서 10MB |
| **파일명** | 경로 순회 차단 (`../` 금지), UUID 재생성 |
| **MIME 검증** | Content-Type + 파일 매직 바이트 이중 검증 (python-magic) |
| **업로드 방식** | S3 Presigned URL 직접 업로드 (서버 부하 분산) |
| **접근 제어** | Private ACL, 조회 시 Presigned URL 발급 (TTL: 1시간) |

```python
# utils/file_validation.py
import magic

ALLOWED_MIMES = {
    "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
    "video": ["video/mp4", "video/quicktime", "video/x-msvideo"],
    "document": ["application/pdf"],
}
MAX_SIZES = {"image": 20_971_520, "video": 524_288_000, "document": 10_485_760}

def validate_file(file_bytes: bytes, content_type: str, file_type: str) -> bool:
    # 1. MIME from Content-Type header
    if content_type not in ALLOWED_MIMES.get(file_type, []):
        raise ValueError(f"Invalid content type: {content_type}")
    # 2. Magic bytes 검증
    detected_mime = magic.from_buffer(file_bytes[:2048], mime=True)
    if detected_mime not in ALLOWED_MIMES[file_type]:
        raise ValueError(f"MIME mismatch: header={content_type}, detected={detected_mime}")
    # 3. 크기 검증
    if len(file_bytes) > MAX_SIZES[file_type]:
        raise ValueError(f"File too large for {file_type}")
    return True
```

### S3 Presigned URL 업로드 플로우

```
1. 클라이언트: POST /contents/{id}/upload { filename, content_type, size }
2. 서버: 파일 검증 (타입, 크기) → S3 Presigned PUT URL 생성 (TTL: 15분)
3. 응답: { upload_url, file_key, expires_in }
4. 클라이언트: 직접 S3에 PUT 업로드 (서버 경유 X)
5. 클라이언트: 업로드 완료 알림 → 서버가 media_urls JSONB 업데이트
```
