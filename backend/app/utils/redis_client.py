"""Redis client helper -- provides async Redis connection."""
import logging

from redis.asyncio import Redis, from_url

from app.config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


async def get_redis() -> Redis:
    """Get or create async Redis client."""
    global _redis
    if _redis is None:
        try:
            _redis = from_url(settings.REDIS_URL, decode_responses=True)
            await _redis.ping()
            logger.info("Redis connected: %s", settings.REDIS_URL)
        except Exception:
            logger.warning("Redis unavailable, operations will use fallback")
            _redis = None
            raise
    return _redis


async def close_redis():
    """Close Redis connection."""
    global _redis
    if _redis:
        await _redis.close()
        _redis = None
