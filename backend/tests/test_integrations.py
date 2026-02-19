"""Tests for SNS platform integrations and resilience patterns."""
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest


def _resp(status_code: int = 200, json_data: dict | None = None) -> httpx.Response:
    """Create an httpx.Response with a proper request set."""
    resp = httpx.Response(
        status_code,
        json=json_data or {},
        request=httpx.Request("GET", "https://test.com"),
    )
    return resp

from app.integrations.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    RateLimiter,
    retry_with_backoff,
    get_circuit_breaker,
    PLATFORM_LIMITS,
)


# ═══════════════════════════════════════════════════════
# Circuit Breaker Tests
# ═══════════════════════════════════════════════════════


class TestCircuitBreaker:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED

    async def test_success_keeps_closed(self):
        cb = CircuitBreaker("test")
        result = await cb.call(AsyncMock(return_value="ok"))
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    async def test_failures_open_circuit(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        failing = AsyncMock(side_effect=Exception("fail"))

        for _ in range(3):
            with pytest.raises(Exception, match="fail"):
                await cb.call(failing)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    async def test_open_circuit_blocks_calls(self):
        cb = CircuitBreaker("test", failure_threshold=1, open_timeout=30)
        failing = AsyncMock(side_effect=Exception("fail"))

        with pytest.raises(Exception):
            await cb.call(failing)

        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitOpenError):
            await cb.call(AsyncMock(return_value="ok"))

    async def test_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, open_timeout=0.1)
        failing = AsyncMock(side_effect=Exception("fail"))

        with pytest.raises(Exception):
            await cb.call(failing)

        assert cb.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Should transition to HALF_OPEN and allow one call
        result = await cb.call(AsyncMock(return_value="recovered"))
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED

    async def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test", failure_threshold=1, open_timeout=0.1)

        with pytest.raises(Exception):
            await cb.call(AsyncMock(side_effect=Exception("fail")))

        assert cb.state == CircuitState.OPEN
        await asyncio.sleep(0.15)

        # HALF_OPEN, but fails again
        with pytest.raises(Exception):
            await cb.call(AsyncMock(side_effect=Exception("still failing")))

        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        cb = CircuitBreaker("test")
        cb.state = CircuitState.OPEN
        cb.failure_count = 5
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_get_circuit_breaker(self):
        cb = get_circuit_breaker("instagram")
        assert cb.name == "instagram"
        assert get_circuit_breaker("instagram") is cb  # same instance


# ═══════════════════════════════════════════════════════
# Rate Limiter Tests
# ═══════════════════════════════════════════════════════


class TestRateLimiter:
    def test_under_limit(self):
        rl = RateLimiter()
        assert rl.check("instagram") is True
        rl.record("instagram")
        assert rl.check("instagram") is True

    def test_over_limit(self):
        rl = RateLimiter()
        limit = PLATFORM_LIMITS["instagram"]
        # Fill up to limit
        for _ in range(limit):
            rl.record("instagram")
        assert rl.check("instagram") is False

    def test_reset_clears_counter(self):
        rl = RateLimiter()
        for _ in range(100):
            rl.record("facebook")
        rl.reset("facebook")
        assert rl.check("facebook") is True

    def test_unknown_platform_uses_default(self):
        rl = RateLimiter()
        assert rl.check("tiktok") is True


# ═══════════════════════════════════════════════════════
# Retry with Backoff Tests
# ═══════════════════════════════════════════════════════


class TestRetryWithBackoff:
    async def test_success_no_retry(self):
        func = AsyncMock(return_value="ok")
        result = await retry_with_backoff(func, max_retries=3, backoff_base=0.01)
        assert result == "ok"
        assert func.call_count == 1

    async def test_retry_on_failure_then_success(self):
        func = AsyncMock(side_effect=[
            httpx.HTTPStatusError("", request=MagicMock(), response=MagicMock(status_code=500)),
            "success",
        ])
        result = await retry_with_backoff(func, max_retries=3, backoff_base=0.01)
        assert result == "success"
        assert func.call_count == 2

    async def test_max_retries_exceeded(self):
        error = httpx.HTTPStatusError("", request=MagicMock(), response=MagicMock(status_code=502))
        func = AsyncMock(side_effect=error)

        with pytest.raises(httpx.HTTPStatusError):
            await retry_with_backoff(func, max_retries=2, backoff_base=0.01)
        assert func.call_count == 3  # initial + 2 retries

    async def test_non_retryable_status_fails_immediately(self):
        error = httpx.HTTPStatusError("", request=MagicMock(), response=MagicMock(status_code=400))
        func = AsyncMock(side_effect=error)

        with pytest.raises(httpx.HTTPStatusError):
            await retry_with_backoff(func, max_retries=3, backoff_base=0.01)
        assert func.call_count == 1  # no retries for 400

    async def test_retry_on_429(self):
        error = httpx.HTTPStatusError("", request=MagicMock(), response=MagicMock(status_code=429))
        func = AsyncMock(side_effect=[error, "ok"])

        result = await retry_with_backoff(func, max_retries=3, backoff_base=0.01)
        assert result == "ok"
        assert func.call_count == 2


# ═══════════════════════════════════════════════════════
# Meta Client Tests (mocked HTTP)
# ═══════════════════════════════════════════════════════


class TestMetaGraphClient:
    async def test_get_me(self):
        from app.integrations.meta.client import MetaGraphClient

        client = MetaGraphClient("fake-token")
        mock_resp = _resp(200, {"id": "123", "name": "Test Page", "username": "testpage"})

        with patch.object(client._client, "get", return_value=mock_resp):
            result = await client.get_me()
            assert result["id"] == "123"
            assert result["name"] == "Test Page"

        await client.close()

    async def test_publish_photo(self):
        from app.integrations.meta.client import MetaGraphClient

        client = MetaGraphClient("fake-token")
        container_resp = _resp(200, {"id": "container_123"})
        publish_resp = _resp(200, {"id": "media_456"})

        with patch.object(client._client, "post", side_effect=[container_resp, publish_resp]):
            result = await client.publish_photo("ig_user_1", "https://example.com/img.jpg", "Caption")
            assert result["id"] == "media_456"

        await client.close()

    async def test_get_comments(self):
        from app.integrations.meta.client import MetaGraphClient

        client = MetaGraphClient("fake-token")
        mock_resp = _resp(200, {
            "data": [{"id": "c1", "text": "Nice!", "username": "user1"}],
        })

        with patch.object(client._client, "get", return_value=mock_resp):
            result = await client.get_comments("media_123")
            assert len(result["data"]) == 1

        await client.close()

    async def test_reply_to_comment(self):
        from app.integrations.meta.client import MetaGraphClient

        client = MetaGraphClient("fake-token")
        mock_resp = _resp(200, {"id": "reply_1"})

        with patch.object(client._client, "post", return_value=mock_resp):
            result = await client.reply_to_comment("c1", "Thanks!")
            assert result["id"] == "reply_1"

        await client.close()


# ═══════════════════════════════════════════════════════
# Meta Publisher Tests
# ═══════════════════════════════════════════════════════


class TestMetaPublisher:
    async def test_publish_instagram_feed(self):
        from app.integrations.meta.client import MetaGraphClient
        from app.integrations.meta.publisher import MetaPublisher

        client = MetaGraphClient("fake-token")
        publisher = MetaPublisher(client)

        container_resp = _resp(200, {"id": "c1"})
        publish_resp = _resp(200, {"id": "m1"})

        with patch.object(client._client, "post", side_effect=[container_resp, publish_resp]):
            result = await publisher.publish("instagram", "ig1", "feed", "Test", media_url="https://img.jpg")
            assert result["id"] == "m1"

        await client.close()

    async def test_publish_facebook_post(self):
        from app.integrations.meta.client import MetaGraphClient
        from app.integrations.meta.publisher import MetaPublisher

        client = MetaGraphClient("fake-token")
        publisher = MetaPublisher(client)

        mock_resp = _resp(200, {"id": "post_1"})
        with patch.object(client._client, "post", return_value=mock_resp):
            result = await publisher.publish("facebook", "page1", "feed", "Hello!")
            assert result["id"] == "post_1"

        await client.close()

    async def test_publish_unsupported_platform_raises(self):
        from app.integrations.meta.client import MetaGraphClient
        from app.integrations.meta.publisher import MetaPublisher

        client = MetaGraphClient("fake-token")
        publisher = MetaPublisher(client)

        with pytest.raises(ValueError, match="Unsupported platform"):
            await publisher.publish("tiktok", "acc1", "feed", "Test")

        await client.close()


# ═══════════════════════════════════════════════════════
# YouTube Client Tests (mocked HTTP)
# ═══════════════════════════════════════════════════════


class TestYouTubeClient:
    async def test_get_my_channel(self):
        from app.integrations.youtube.client import YouTubeClient

        client = YouTubeClient("fake-token")
        mock_resp = _resp(200, {
            "items": [{"id": "ch1", "snippet": {"title": "My Channel"}, "statistics": {"subscriberCount": "1000"}}]
        })

        with patch.object(client._client, "get", return_value=mock_resp):
            result = await client.get_my_channel()
            assert result["items"][0]["id"] == "ch1"

        await client.close()

    async def test_get_channel_stats(self):
        from app.integrations.youtube.client import YouTubeClient

        client = YouTubeClient("fake-token")
        mock_resp = _resp(200, {
            "items": [{"statistics": {"subscriberCount": "500", "viewCount": "10000"}}]
        })

        with patch.object(client._client, "get", return_value=mock_resp):
            stats = await client.get_channel_stats("ch1")
            assert stats["subscriberCount"] == "500"

        await client.close()

    async def test_get_comments(self):
        from app.integrations.youtube.client import YouTubeClient

        client = YouTubeClient("fake-token")
        mock_resp = _resp(200, {
            "items": [{"snippet": {"topLevelComment": {"snippet": {"textOriginal": "Great!"}}}}]
        })

        with patch.object(client._client, "get", return_value=mock_resp):
            result = await client.get_comments("vid1")
            assert len(result["items"]) == 1

        await client.close()

    async def test_reply_to_comment(self):
        from app.integrations.youtube.client import YouTubeClient

        client = YouTubeClient("fake-token")
        mock_resp = _resp(200, {"id": "reply_yt_1"})

        with patch.object(client._client, "post", return_value=mock_resp):
            result = await client.reply_to_comment("parent_c1", "Thanks for watching!")
            assert result["id"] == "reply_yt_1"

        await client.close()


# ═══════════════════════════════════════════════════════
# YouTube Insights Tests
# ═══════════════════════════════════════════════════════


class TestYouTubeInsights:
    async def test_collect_channel_insights(self):
        from app.integrations.youtube.client import YouTubeClient
        from app.integrations.youtube.insights import YouTubeInsightsCollector

        client = YouTubeClient("fake-token")
        collector = YouTubeInsightsCollector(client)

        mock_resp = _resp(200, {
            "items": [{"statistics": {"subscriberCount": "1200", "viewCount": "50000", "videoCount": "30"}}]
        })

        with patch.object(client._client, "get", return_value=mock_resp):
            insights = await collector.collect_channel_insights("ch1")
            assert insights["subscribers"] == 1200
            assert insights["views"] == 50000
            assert insights["videos"] == 30

        await client.close()

    async def test_collect_video_insights(self):
        from app.integrations.youtube.client import YouTubeClient
        from app.integrations.youtube.insights import YouTubeInsightsCollector

        client = YouTubeClient("fake-token")
        collector = YouTubeInsightsCollector(client)

        mock_resp = _resp(200, {
            "items": [{
                "snippet": {"title": "Test Video", "publishedAt": "2026-01-01"},
                "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "10"},
            }]
        })

        with patch.object(client._client, "get", return_value=mock_resp):
            insights = await collector.collect_video_insights("vid1")
            assert insights["title"] == "Test Video"
            assert insights["views"] == 1000
            assert insights["likes"] == 50

        await client.close()
