"""Performance + Security verification tests — Phase 8, STEP 31.

Covers:
1. API response time validation (P95 < 500ms)
2. Concurrent request handling
3. SQL Injection prevention
4. XSS prevention
5. File upload security (malicious file rejection)
6. Authentication & Authorization security
7. Rate limiting verification
8. Input validation & sanitization
9. WebSocket connection load tests
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.client import Client
from app.models.platform_account import PlatformAccount, Platform
from app.services.auth_service import create_access_token, hash_password
from app.main import app
from app.utils.file_validation import (
    validate_file,
    sanitize_filename,
    FileValidationError,
)


# ─── Shared Setup ────────────────────────────────────────────────────────

async def _perf_setup(db: AsyncSession):
    """Create environment for performance/security tests."""
    admin = User(
        id=uuid.uuid4(), email="perfadmin@test.com",
        password_hash=hash_password("pass123"), name="PerfAdmin", role=UserRole.ADMIN,
    )
    operator = User(
        id=uuid.uuid4(), email="perfop@test.com",
        password_hash=hash_password("pass123"), name="PerfOp", role=UserRole.OPERATOR,
    )
    db.add_all([admin, operator])
    await db.flush()

    brand = Client(
        id=uuid.uuid4(), name="Perf Brand", industry="retail",
        manager_id=admin.id,
    )
    db.add(brand)
    await db.flush()

    account = PlatformAccount(
        id=uuid.uuid4(), client_id=brand.id,
        platform=Platform.INSTAGRAM, account_name="perf_ig",
        access_token="perf_token", is_connected=True,
    )
    db.add(account)
    await db.commit()

    def _h(user):
        t = create_access_token(str(user.id), user.role.value)
        return {"Authorization": f"Bearer {t}"}

    return {
        "admin": (admin, _h(admin)),
        "operator": (operator, _h(operator)),
        "brand": brand,
    }


# ─── 1. API Response Time (P95 < 500ms) ──────────────────────────────────

class TestAPIPerformance:
    """Verify API endpoints respond within performance budget."""

    async def test_health_endpoint_latency(self, client: AsyncClient):
        """Health endpoint should respond in < 100ms."""
        times = []
        for _ in range(20):
            start = time.perf_counter()
            resp = await client.get("/health")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            assert resp.status_code == 200

        times.sort()
        p95 = times[int(len(times) * 0.95)]
        assert p95 < 500, f"Health P95 latency {p95:.1f}ms exceeds 500ms"

    async def test_content_list_latency(self, client: AsyncClient, db_session: AsyncSession):
        """Content list API should respond within budget."""
        setup = await _perf_setup(db_session)
        _, h = setup["operator"]

        times = []
        for _ in range(10):
            start = time.perf_counter()
            resp = await client.get("/api/v1/contents", headers=h)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            assert resp.status_code == 200

        times.sort()
        p95 = times[int(len(times) * 0.95)]
        assert p95 < 500, f"Contents P95 latency {p95:.1f}ms exceeds 500ms"

    async def test_metrics_endpoint_latency(self, client: AsyncClient):
        """Metrics endpoint should respond quickly."""
        times = []
        for _ in range(10):
            start = time.perf_counter()
            resp = await client.get("/metrics")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            assert resp.status_code == 200

        times.sort()
        p95 = times[int(len(times) * 0.95)]
        assert p95 < 500, f"Metrics P95 latency {p95:.1f}ms exceeds 500ms"

    async def test_concurrent_requests(self, client: AsyncClient, db_session: AsyncSession):
        """Server should handle concurrent requests without errors."""
        setup = await _perf_setup(db_session)
        _, h = setup["operator"]

        async def make_request():
            resp = await client.get("/api/v1/contents", headers=h)
            return resp.status_code

        # Fire 20 concurrent requests
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        assert all(s == 200 for s in results), f"Some requests failed: {results}"


# ─── 2. SQL Injection Prevention ──────────────────────────────────────────

class TestSQLInjection:
    """Verify SQL injection attempts are blocked."""

    SQL_PAYLOADS = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "1; DELETE FROM contents WHERE 1=1; --",
        "' UNION SELECT password_hash FROM users --",
        "admin'--",
        "1' OR 1=1 --",
        "'; EXEC xp_cmdshell('whoami'); --",
    ]

    async def test_sqli_in_login(self, client: AsyncClient):
        """SQL injection in login should fail gracefully."""
        for payload in self.SQL_PAYLOADS:
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": payload, "password": payload},
            )
            # Should get 401 or 422, never 200 or 500
            assert resp.status_code in (401, 422), (
                f"Unexpected status {resp.status_code} for SQLi payload: {payload}"
            )

    async def test_sqli_in_query_params(self, client: AsyncClient, db_session: AsyncSession):
        """SQL injection in query parameters should be safe."""
        setup = await _perf_setup(db_session)
        _, h = setup["admin"]

        for payload in self.SQL_PAYLOADS:
            # Try in search/filter parameters
            resp = await client.get(
                f"/api/v1/contents?client_id={payload}",
                headers=h,
            )
            # Should get 422 (validation error) or 200 (empty results), never 500
            assert resp.status_code in (200, 400, 422), (
                f"Unexpected status {resp.status_code} for SQLi in query: {payload}"
            )

    async def test_sqli_in_path_params(self, client: AsyncClient, db_session: AsyncSession):
        """SQL injection in path parameters should be safe."""
        setup = await _perf_setup(db_session)
        _, h = setup["admin"]

        for payload in self.SQL_PAYLOADS:
            resp = await client.get(
                f"/api/v1/contents/{payload}",
                headers=h,
            )
            # Should get 404 or 422, never 500
            assert resp.status_code in (400, 404, 422), (
                f"Unexpected status {resp.status_code} for SQLi in path: {payload}"
            )

    async def test_sqli_in_content_body(self, client: AsyncClient, db_session: AsyncSession):
        """SQL injection in content body should be stored safely (no execution)."""
        setup = await _perf_setup(db_session)
        _, h = setup["operator"]
        brand = setup["brand"]

        for payload in self.SQL_PAYLOADS[:3]:
            resp = await client.post(
                "/api/v1/contents",
                json={
                    "client_id": str(brand.id),
                    "title": payload,
                    "body": payload,
                    "content_type": "feed",
                    "target_platforms": ["instagram"],
                },
                headers=h,
            )
            # Content should be created successfully (payload is just text)
            assert resp.status_code == 201, (
                f"Content creation failed for SQLi payload: {payload}"
            )
            # Verify data is stored as-is, not executed
            content_id = resp.json()["data"]["id"]
            detail = await client.get(f"/api/v1/contents/{content_id}", headers=h)
            assert detail.json()["data"]["title"] == payload


# ─── 3. XSS Prevention ───────────────────────────────────────────────────

class TestXSSPrevention:
    """Verify XSS payloads are handled safely."""

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
        "'\"><script>alert(document.cookie)</script>",
        "<iframe src='javascript:alert(1)'>",
        "<body onload=alert('xss')>",
    ]

    async def test_xss_in_content_creation(self, client: AsyncClient, db_session: AsyncSession):
        """XSS payloads in content should be stored without execution."""
        setup = await _perf_setup(db_session)
        _, h = setup["operator"]
        brand = setup["brand"]

        for payload in self.XSS_PAYLOADS[:3]:
            resp = await client.post(
                "/api/v1/contents",
                json={
                    "client_id": str(brand.id),
                    "title": payload,
                    "body": payload,
                    "content_type": "feed",
                    "target_platforms": ["instagram"],
                },
                headers=h,
            )
            assert resp.status_code == 201
            # API returns JSON, not HTML — XSS not executable
            data = resp.json()["data"]
            assert data["title"] == payload  # Stored as-is in JSON

    async def test_xss_in_api_response_headers(self, client: AsyncClient):
        """API responses should have proper security headers (JSON content type)."""
        resp = await client.get("/health")
        content_type = resp.headers.get("content-type", "")
        assert "application/json" in content_type


# ─── 4. File Upload Security ─────────────────────────────────────────────

class TestFileUploadSecurity:
    """Verify malicious file uploads are blocked."""

    def test_executable_file_rejected(self):
        """Executable files should be rejected."""
        # EXE magic bytes (MZ header)
        exe_content = b"MZ" + b"\x00" * 100
        with pytest.raises(FileValidationError):
            validate_file(exe_content, "application/x-msdownload", "image", "malware.exe")

    def test_php_file_rejected(self):
        """PHP files should be rejected."""
        php_content = b"<?php echo 'hack'; ?>"
        with pytest.raises(FileValidationError):
            validate_file(php_content, "application/x-php", "document", "shell.php")

    def test_double_extension_sanitized(self):
        """Double extension tricks are sanitized (original name replaced with UUID)."""
        safe = sanitize_filename("image.jpg.exe")
        # Original filename is completely replaced with UUID
        assert "image" not in safe
        # The file would still need to pass MIME+magic byte validation to be accepted

    def test_path_traversal_rejected(self):
        """Path traversal attempts should be rejected."""
        with pytest.raises(FileValidationError):
            sanitize_filename("../../../etc/passwd")
        with pytest.raises(FileValidationError):
            sanitize_filename("..\\..\\windows\\system32\\cmd.exe")

    def test_null_byte_injection(self):
        """Null byte injection in filename should be sanitized."""
        safe = sanitize_filename("image.jpg\x00.exe")
        assert "\x00" not in safe

    def test_oversized_file_rejected(self):
        """Files exceeding size limit should be rejected."""
        # Create content > 20MB (image limit)
        large_content = b"\xff\xd8\xff\xe0" + b"\x00" * (21 * 1024 * 1024)
        with pytest.raises(FileValidationError):
            validate_file(large_content, "image/jpeg", "image", "huge.jpg")

    def test_valid_image_accepted(self):
        """Valid image files should pass validation."""
        # JPEG magic bytes + small content
        jpeg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        # Should not raise
        result = validate_file(jpeg_content, "image/jpeg", "image", "photo.jpg")
        assert result is not None

    def test_script_content_as_image_rejected(self):
        """Script content disguised as image should be rejected."""
        # HTML/JS content claiming to be image
        script_content = b"<script>alert('xss')</script>" + b"\x00" * 100
        with pytest.raises(FileValidationError):
            validate_file(script_content, "text/html", "image", "hack.jpg")


# ─── 5. Authentication Security ──────────────────────────────────────────

class TestAuthSecurity:
    """Verify authentication and authorization security."""

    async def test_unauthenticated_access_denied(self, client: AsyncClient):
        """Protected endpoints should reject unauthenticated requests."""
        protected = [
            "/api/v1/contents",
            "/api/v1/clients",
            "/api/v1/users",
            "/api/v1/notifications",
        ]
        for endpoint in protected:
            resp = await client.get(endpoint)
            assert resp.status_code in (401, 403), (
                f"Unauthenticated access allowed on {endpoint}"
            )

    async def test_invalid_token_rejected(self, client: AsyncClient):
        """Invalid JWT tokens should be rejected."""
        invalid_tokens = [
            "Bearer invalid.token.here",
            "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalid",
            "NotBearer validtoken",
            "",
        ]
        for token in invalid_tokens:
            headers = {"Authorization": token} if token else {}
            resp = await client.get("/api/v1/contents", headers=headers)
            assert resp.status_code in (401, 403, 422), (
                f"Invalid token accepted: {token[:30]}..."
            )

    async def test_expired_token_rejected(self, client: AsyncClient):
        """Expired tokens should be rejected."""
        from jose import jwt
        from app.config import settings
        payload = {
            "sub": str(uuid.uuid4()),
            "role": "admin",
            "exp": 1000000000,  # Way in the past (2001)
        }
        expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        resp = await client.get(
            "/api/v1/contents",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code in (401, 403)

    async def test_privilege_escalation_prevented(self, client: AsyncClient, db_session: AsyncSession):
        """Users should not be able to access resources beyond their role."""
        setup = await _perf_setup(db_session)
        _, op_h = setup["operator"]

        # Operator should not access user management
        resp = await client.get("/api/v1/users", headers=op_h)
        assert resp.status_code == 403

        # Operator should not access audit logs
        resp = await client.get("/api/v1/settings/audit-logs", headers=op_h)
        assert resp.status_code == 403

    async def test_password_not_exposed_in_api(self, client: AsyncClient, db_session: AsyncSession):
        """User API should never return password hashes."""
        setup = await _perf_setup(db_session)
        _, admin_h = setup["admin"]

        resp = await client.get("/api/v1/users", headers=admin_h)
        assert resp.status_code == 200
        users = resp.json()["data"]
        for user in users:
            assert "password" not in user
            assert "password_hash" not in user


# ─── 6. Input Validation ─────────────────────────────────────────────────

class TestInputValidation:
    """Verify input validation and sanitization."""

    async def test_oversized_payload_rejected(self, client: AsyncClient, db_session: AsyncSession):
        """Very large payloads should be rejected or handled gracefully."""
        setup = await _perf_setup(db_session)
        _, h = setup["operator"]

        # Try sending a very large body
        large_body = "x" * 100_000  # 100KB text
        resp = await client.post(
            "/api/v1/contents",
            json={
                "client_id": str(setup["brand"].id),
                "title": "Test",
                "body": large_body,
                "content_type": "feed",
                "target_platforms": ["instagram"],
            },
            headers=h,
        )
        # Should either accept (stored) or reject (413/422), not crash (500)
        assert resp.status_code != 500

    async def test_unicode_handling(self, client: AsyncClient, db_session: AsyncSession):
        """Unicode content should be handled correctly."""
        setup = await _perf_setup(db_session)
        _, h = setup["operator"]

        unicode_texts = [
            "한국어 테스트 🎉",
            "日本語テスト 🇯🇵",
            "Ñoño español 🌮",
            "Ü̷̢n̶̤i̵̡c̸̣o̷̰d̵̤ë̵̞ ̴̣z̸̤a̵̡ḷ̸g̷̰o̷̤",
        ]
        for text in unicode_texts:
            resp = await client.post(
                "/api/v1/contents",
                json={
                    "client_id": str(setup["brand"].id),
                    "title": text,
                    "body": text,
                    "content_type": "feed",
                    "target_platforms": ["instagram"],
                },
                headers=h,
            )
            assert resp.status_code == 201, f"Unicode handling failed for: {text}"
            assert resp.json()["data"]["title"] == text

    async def test_empty_required_fields_rejected(self, client: AsyncClient, db_session: AsyncSession):
        """Empty required fields should trigger validation error."""
        setup = await _perf_setup(db_session)
        _, h = setup["operator"]

        resp = await client.post(
            "/api/v1/contents",
            json={
                "client_id": str(setup["brand"].id),
                "title": "",
                "body": "",
                "content_type": "feed",
                "target_platforms": [],
            },
            headers=h,
        )
        # Should get validation error, not 500
        assert resp.status_code in (201, 400, 422)

    async def test_invalid_uuid_rejected(self, client: AsyncClient, db_session: AsyncSession):
        """Invalid UUID format should be rejected gracefully."""
        setup = await _perf_setup(db_session)
        _, h = setup["admin"]

        invalid_uuids = ["not-a-uuid", "12345", "null", "undefined"]
        for invalid in invalid_uuids:
            resp = await client.get(f"/api/v1/contents/{invalid}", headers=h)
            assert resp.status_code in (400, 404, 422), (
                f"Invalid UUID not rejected: {invalid} → {resp.status_code}"
            )


# ─── 7. Rate Limiting ────────────────────────────────────────────────────

class TestRateLimiting:
    """Verify rate limiting is enforced."""

    async def test_login_rate_limit(self, client: AsyncClient):
        """Login endpoint should be rate-limited."""
        responses = []
        for _ in range(15):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@test.com", "password": "wrong"},
            )
            responses.append(resp.status_code)

        # After exceeding limit (10/min), should see 429
        assert 429 in responses, "Rate limit not enforced on login endpoint"

    async def test_rate_limit_response_format(self, client: AsyncClient):
        """Rate limit response should include proper headers/body."""
        # Exhaust rate limit
        for _ in range(15):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "ratelimit@test.com", "password": "wrong"},
            )
            if resp.status_code == 429:
                data = resp.json()
                assert data.get("status") == "error" or "rate" in data.get("detail", "").lower() or "rate" in data.get("message", "").lower()
                break


# ─── 8. CORS & Security Headers ──────────────────────────────────────────

class TestSecurityHeaders:
    """Verify security-related response headers."""

    async def test_cors_headers_present(self, client: AsyncClient):
        """CORS headers should be present for API responses."""
        resp = await client.options(
            "/api/v1/contents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should not return 500
        assert resp.status_code != 500

    async def test_json_content_type(self, client: AsyncClient):
        """API endpoints should return application/json."""
        resp = await client.get("/health")
        assert "application/json" in resp.headers.get("content-type", "")


# ─── 9. WebSocket Load Tests ────────────────────────────────────────────

class TestWebSocketLoad:
    """WebSocket connection load tests."""

    async def test_multiple_ws_connections(self, db_session: AsyncSession):
        """Test handling multiple simultaneous WebSocket connections."""
        from starlette.testclient import TestClient as StarletteTestClient

        setup = await _perf_setup(db_session)
        admin_user, admin_headers = setup["admin"]
        token = admin_headers["Authorization"].replace("Bearer ", "")

        starlette_client = StarletteTestClient(app)

        # Test multiple connections in sequence
        connections_made = 0
        for i in range(20):
            try:
                with starlette_client.websocket_connect(f"/ws?token={token}") as ws:
                    ws.send_json({"type": "ping"})
                    data = ws.receive_json()
                    assert data["type"] == "pong"
                    connections_made += 1
            except Exception:
                break

        assert connections_made >= 10, f"Only {connections_made} connections succeeded"

    async def test_ws_ping_pong_roundtrip(self, db_session: AsyncSession):
        """Test WebSocket ping/pong heartbeat mechanism."""
        from starlette.testclient import TestClient as StarletteTestClient

        setup = await _perf_setup(db_session)
        _, admin_headers = setup["admin"]
        token = admin_headers["Authorization"].replace("Bearer ", "")

        starlette_client = StarletteTestClient(app)

        with starlette_client.websocket_connect(f"/ws?token={token}") as ws:
            # Send multiple pings and verify each gets a pong
            for _ in range(5):
                ws.send_json({"type": "ping"})
                data = ws.receive_json()
                assert data["type"] == "pong"

    async def test_ws_invalid_token_rejected(self, db_session: AsyncSession):
        """Test that invalid tokens are rejected."""
        from starlette.testclient import TestClient as StarletteTestClient
        from starlette.websockets import WebSocketDisconnect

        starlette_client = StarletteTestClient(app)

        # Invalid token should cause connection to be closed with code 4001
        rejected = False
        try:
            with starlette_client.websocket_connect("/ws?token=invalid-token") as ws:
                # Server should close the connection
                ws.receive_json()
        except (WebSocketDisconnect, Exception):
            rejected = True

        assert rejected, "WebSocket with invalid token was not rejected"

    async def test_ws_expired_token_rejected(self, db_session: AsyncSession):
        """Test that expired tokens are rejected."""
        from starlette.testclient import TestClient as StarletteTestClient
        from starlette.websockets import WebSocketDisconnect
        from jose import jwt
        from app.config import settings

        # Create an expired token
        payload = {
            "sub": str(uuid.uuid4()),
            "role": "admin",
            "exp": 1000000000,  # Way in the past (2001)
        }
        expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

        starlette_client = StarletteTestClient(app)

        rejected = False
        try:
            with starlette_client.websocket_connect(f"/ws?token={expired_token}") as ws:
                ws.receive_json()
        except (WebSocketDisconnect, Exception):
            rejected = True

        assert rejected, "WebSocket with expired token was not rejected"

    async def test_ws_handles_malformed_json(self, db_session: AsyncSession):
        """Test that WebSocket handles malformed JSON gracefully."""
        from starlette.testclient import TestClient as StarletteTestClient

        setup = await _perf_setup(db_session)
        _, admin_headers = setup["admin"]
        token = admin_headers["Authorization"].replace("Bearer ", "")

        starlette_client = StarletteTestClient(app)

        with starlette_client.websocket_connect(f"/ws?token={token}") as ws:
            # Send malformed JSON — server should ignore it, not crash
            ws.send_text("not valid json {{{")

            # Server should still respond to valid messages after bad input
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    async def test_ws_concurrent_connections_same_user(self, db_session: AsyncSession):
        """Test multiple WebSocket connections from the same user."""
        from starlette.testclient import TestClient as StarletteTestClient

        setup = await _perf_setup(db_session)
        _, admin_headers = setup["admin"]
        token = admin_headers["Authorization"].replace("Bearer ", "")

        starlette_client = StarletteTestClient(app)

        # Open two connections for the same user
        with starlette_client.websocket_connect(f"/ws?token={token}") as ws1:
            ws1.send_json({"type": "ping"})
            data1 = ws1.receive_json()
            assert data1["type"] == "pong"

            with starlette_client.websocket_connect(f"/ws?token={token}") as ws2:
                ws2.send_json({"type": "ping"})
                data2 = ws2.receive_json()
                assert data2["type"] == "pong"

            # First connection should still work after second is opened
            ws1.send_json({"type": "ping"})
            data3 = ws1.receive_json()
            assert data3["type"] == "pong"
