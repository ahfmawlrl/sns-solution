"""Tests for Phase 6: File validation, Rate limiting, Audit middleware."""
import uuid
import time
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.utils.file_validation import (
    FileValidationError,
    detect_mime_by_magic,
    validate_content_type,
    validate_file_size,
    validate_magic_bytes,
    sanitize_filename,
    validate_file,
    generate_s3_key,
    ALLOWED_MIMES,
    MAX_SIZES,
)
from app.middleware.rate_limiter import RateLimitMiddleware, _memory_store, check_rate_limit_redis
from app.middleware.audit_middleware import _extract_resource_info


# ─── File Validation ────────────────────────────────────────────────────

class TestFileValidation:
    """Tests for file validation utilities."""

    def test_validate_content_type_valid_image(self):
        validate_content_type("image/jpeg", "image")

    def test_validate_content_type_valid_video(self):
        validate_content_type("video/mp4", "video")

    def test_validate_content_type_valid_document(self):
        validate_content_type("application/pdf", "document")

    def test_validate_content_type_invalid(self):
        with pytest.raises(FileValidationError, match="Invalid content type"):
            validate_content_type("application/zip", "image")

    def test_validate_content_type_unknown_type(self):
        with pytest.raises(FileValidationError, match="Unknown file type"):
            validate_content_type("text/plain", "executable")

    def test_validate_file_size_within_limit(self):
        validate_file_size(1000, "image")  # 1 KB < 20 MB

    def test_validate_file_size_exceeds_limit(self):
        with pytest.raises(FileValidationError, match="File too large"):
            validate_file_size(MAX_SIZES["image"] + 1, "image")

    def test_validate_file_size_exact_limit(self):
        validate_file_size(MAX_SIZES["image"], "image")  # should pass

    def test_validate_file_size_video_limit(self):
        with pytest.raises(FileValidationError, match="File too large"):
            validate_file_size(MAX_SIZES["video"] + 1, "video")

    def test_detect_mime_jpeg(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        assert detect_mime_by_magic(data) == "image/jpeg"

    def test_detect_mime_png(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert detect_mime_by_magic(data) == "image/png"

    def test_detect_mime_gif(self):
        data = b"GIF89a" + b"\x00" * 100
        assert detect_mime_by_magic(data) == "image/gif"

    def test_detect_mime_pdf(self):
        data = b"%PDF-1.4" + b"\x00" * 100
        assert detect_mime_by_magic(data) == "application/pdf"

    def test_detect_mime_mp4(self):
        data = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100
        assert detect_mime_by_magic(data) == "video/mp4"

    def test_detect_mime_unknown(self):
        data = b"\x00\x01\x02\x03" * 10
        assert detect_mime_by_magic(data) is None

    def test_detect_mime_too_short(self):
        assert detect_mime_by_magic(b"\xff\xd8") is None

    def test_sanitize_filename_basic(self):
        result = sanitize_filename("photo.jpg")
        assert result.endswith(".jpg")
        assert len(result) == 36  # 32 hex + 4 (.jpg)

    def test_sanitize_filename_uuid_generated(self):
        result1 = sanitize_filename("test.png")
        result2 = sanitize_filename("test.png")
        assert result1 != result2  # Different UUIDs

    def test_sanitize_filename_path_traversal(self):
        with pytest.raises(FileValidationError, match="path traversal"):
            sanitize_filename("../../etc/passwd")

    def test_sanitize_filename_forward_slash(self):
        with pytest.raises(FileValidationError, match="path traversal"):
            sanitize_filename("dir/file.txt")

    def test_sanitize_filename_backslash(self):
        with pytest.raises(FileValidationError, match="path traversal"):
            sanitize_filename("dir\\file.txt")

    def test_validate_file_full_pipeline_jpeg(self):
        jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        result = validate_file(jpeg_bytes, "image/jpeg", "image", "photo.jpg")
        assert result["safe_filename"].endswith(".jpg")
        assert result["detected_mime"] == "image/jpeg"

    def test_validate_file_full_pipeline_pdf(self):
        pdf_bytes = b"%PDF-1.4" + b"\x00" * 100
        result = validate_file(pdf_bytes, "application/pdf", "document", "report.pdf")
        assert result["safe_filename"].endswith(".pdf")
        assert result["detected_mime"] == "application/pdf"

    def test_validate_file_mime_mismatch(self):
        # Claim JPEG content type but send PNG magic bytes
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        with pytest.raises(FileValidationError, match="Invalid content type"):
            validate_file(png_bytes, "image/png", "document")

    def test_generate_s3_key(self):
        key = generate_s3_key("client-123", "image", "abc.jpg")
        assert key == "clients/client-123/images/abc.jpg"

    def test_generate_s3_key_video(self):
        key = generate_s3_key("c-1", "video", "clip.mp4")
        assert key == "clients/c-1/videos/clip.mp4"

    def test_allowed_mimes_completeness(self):
        assert "image" in ALLOWED_MIMES
        assert "video" in ALLOWED_MIMES
        assert "document" in ALLOWED_MIMES
        assert len(ALLOWED_MIMES["image"]) == 4
        assert len(ALLOWED_MIMES["video"]) == 3
        assert len(ALLOWED_MIMES["document"]) == 1


# ─── Rate Limiter ────────────────────────────────────────────────────────

class TestRateLimiter:
    """Tests for rate limiting middleware."""

    def setup_method(self):
        _memory_store.clear()

    def test_get_limit_default(self):
        middleware = RateLimitMiddleware(app=None)
        limit, window = middleware._get_limit("/api/v1/contents")
        assert limit == 60
        assert window == 60

    def test_get_limit_auth(self):
        middleware = RateLimitMiddleware(app=None)
        limit, window = middleware._get_limit("/api/v1/auth/login")
        assert limit == 10
        assert window == 60

    def test_get_limit_ai(self):
        middleware = RateLimitMiddleware(app=None)
        limit, window = middleware._get_limit("/api/v1/ai/chat")
        assert limit == 20
        assert window == 60

    @pytest.mark.asyncio
    async def test_check_limit_allows_under_limit(self):
        middleware = RateLimitMiddleware(app=None)
        for _ in range(5):
            assert await middleware._check_limit("user1", "/test", 10, 60) is True

    @pytest.mark.asyncio
    async def test_check_limit_blocks_over_limit(self, monkeypatch):
        # Force in-memory fallback by patching get_redis to fail
        monkeypatch.setattr("app.middleware.rate_limiter.check_rate_limit_redis", AsyncMock(side_effect=Exception("no redis")))
        middleware = RateLimitMiddleware(app=None)
        # Use up limit
        for _ in range(3):
            await middleware._check_limit("user2", "/test", 3, 60)
        # Should be blocked
        assert await middleware._check_limit("user2", "/test", 3, 60) is False

    @pytest.mark.asyncio
    async def test_check_limit_different_users_independent(self, monkeypatch):
        monkeypatch.setattr("app.middleware.rate_limiter.check_rate_limit_redis", AsyncMock(side_effect=Exception("no redis")))
        middleware = RateLimitMiddleware(app=None)
        for _ in range(3):
            await middleware._check_limit("userA", "/test", 3, 60)
        # userA is blocked
        assert await middleware._check_limit("userA", "/test", 3, 60) is False
        # userB is still allowed
        assert await middleware._check_limit("userB", "/test", 3, 60) is True

    @pytest.mark.asyncio
    async def test_redis_rate_limit(self):
        """Test Redis-based rate limit helper."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 1
        result = await check_rate_limit_redis(mock_redis, "user1", "/test", 60, 60)
        assert result is True
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_rate_limit_exceeded(self):
        """Test Redis-based rate limit when exceeded."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 61
        result = await check_rate_limit_redis(mock_redis, "user1", "/test", 60, 60)
        assert result is False


# ─── Audit Middleware ────────────────────────────────────────────────────

class TestAuditMiddleware:
    """Tests for audit log extraction utilities."""

    def test_extract_resource_info_contents(self):
        resource, rid = _extract_resource_info("/api/v1/contents")
        assert resource == "content"
        assert rid is None

    def test_extract_resource_info_with_id(self):
        test_id = str(uuid.uuid4())
        resource, rid = _extract_resource_info(f"/api/v1/contents/{test_id}")
        assert resource == "content"
        assert rid == test_id

    def test_extract_resource_info_with_sub_path(self):
        test_id = str(uuid.uuid4())
        resource, rid = _extract_resource_info(f"/api/v1/contents/{test_id}/status")
        assert resource == "content"
        assert rid == test_id

    def test_extract_resource_info_users(self):
        resource, rid = _extract_resource_info("/api/v1/users")
        assert resource == "user"

    def test_extract_resource_info_clients(self):
        resource, rid = _extract_resource_info("/api/v1/clients")
        assert resource == "client"

    def test_extract_resource_info_non_uuid_id(self):
        resource, rid = _extract_resource_info("/api/v1/contents/status")
        assert resource == "content"
        assert rid is None  # "status" is not a UUID

    def test_extract_resource_info_unknown_path(self):
        resource, rid = _extract_resource_info("/some/other/path")
        assert resource == "unknown"


# ─── Integration: Rate Limit via API ────────────────────────────────────

@pytest.fixture
def clear_rate_limit():
    _memory_store.clear()
    yield
    _memory_store.clear()


async def test_health_not_rate_limited(client: AsyncClient, clear_rate_limit):
    """Health check should bypass rate limiting."""
    for _ in range(100):
        resp = await client.get("/health")
        assert resp.status_code == 200


async def test_api_rate_limit_headers(client: AsyncClient, admin_auth, clear_rate_limit):
    """API responses should include rate limit headers."""
    _, headers = admin_auth
    resp = await client.get("/api/v1/users/me", headers=headers)
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Window" in resp.headers


async def test_rate_limit_429_response(client: AsyncClient, clear_rate_limit):
    """Exceeding rate limit should return 429."""
    # Login endpoint has a limit of 10/min
    for i in range(11):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": f"test{i}@test.com", "password": "wrong"},
        )
    # 11th request should be 429
    assert resp.status_code == 429
