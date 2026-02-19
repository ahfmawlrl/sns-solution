"""Redis-based rate limiting middleware.

Supports per-user and per-endpoint rate limiting using Redis INCR + EXPIRE.
Falls back to in-memory dict when Redis is unavailable.
"""
import time
import logging
from collections import defaultdict

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# In-memory fallback when Redis is not available
_memory_store: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with configurable limits per endpoint pattern.

    Default: 60 requests per minute per user.
    Auth endpoints: 10 requests per minute (brute-force protection).
    AI endpoints: 20 requests per minute (expensive operations).
    """

    # Endpoint pattern -> (limit, window_seconds)
    LIMITS: dict[str, tuple[int, int]] = {
        "/api/v1/auth/login": (10, 60),
        "/api/v1/auth/refresh": (20, 60),
        "/api/v1/ai/": (20, 60),
        "default": (60, 60),
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks and docs
        path = request.url.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Identify user (by token sub or IP)
        user_id = self._get_user_identifier(request)
        limit, window = self._get_limit(path)

        # Check rate limit
        is_allowed = await self._check_limit(user_id, path, limit, window)
        if not is_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": "Rate limit exceeded. Please try again later.",
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Window"] = f"{window}s"

        return response

    def _get_user_identifier(self, request: Request) -> str:
        """Extract user identifier from request."""
        # Try Authorization header first
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            # Use a hash of the token for privacy
            token = auth[7:]
            return f"token:{hash(token)}"

        # Fall back to IP
        client = request.client
        ip = client.host if client else "unknown"
        return f"ip:{ip}"

    def _get_limit(self, path: str) -> tuple[int, int]:
        """Get rate limit for the given path."""
        for pattern, limit in self.LIMITS.items():
            if pattern != "default" and path.startswith(pattern):
                return limit
        return self.LIMITS["default"]

    async def _check_limit(
        self, user_id: str, path: str, limit: int, window: int
    ) -> bool:
        """Check if request is within rate limit. Tries Redis first, falls back to in-memory."""
        # Try Redis first
        try:
            from app.utils.redis_client import get_redis
            redis = await get_redis()
            return await check_rate_limit_redis(redis, user_id, path, limit, window)
        except Exception:
            pass

        # Fallback to in-memory
        key = f"ratelimit:{user_id}:{path}"
        now = time.time()
        _memory_store[key] = [t for t in _memory_store[key] if t > now - window]
        if len(_memory_store[key]) >= limit:
            return False
        _memory_store[key].append(now)
        return True


async def check_rate_limit_redis(
    redis_client, user_id: str, endpoint: str, limit: int = 60, window: int = 60
) -> bool:
    """Redis-based rate limit check (for use when Redis is available).

    Args:
        redis_client: aioredis client
        user_id: User identifier
        endpoint: API endpoint path
        limit: Max requests per window
        window: Time window in seconds

    Returns:
        True if allowed, False if rate limited
    """
    key = f"ratelimit:{user_id}:{endpoint}"
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window)
    return current <= limit
