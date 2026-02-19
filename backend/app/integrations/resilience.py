"""Common resilience patterns for external API calls.

- Circuit Breaker (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Retry with Exponential Backoff
- Rate Limit checker
"""
import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ── Rate Limit ──

# Platform API quota limits (requests per hour)
PLATFORM_LIMITS: dict[str, int] = {
    "instagram": 200,
    "facebook": 200,
    "youtube": 10000,
}


class RateLimiter:
    """In-memory rate limiter. In production, use Redis counters."""

    def __init__(self):
        self._counters: dict[str, list[float]] = {}

    def check(self, platform: str) -> bool:
        """Return True if under limit, False if exceeded."""
        limit = PLATFORM_LIMITS.get(platform, 1000)
        now = time.time()
        window = 3600  # 1 hour

        key = platform
        if key not in self._counters:
            self._counters[key] = []

        # Prune old entries
        self._counters[key] = [t for t in self._counters[key] if now - t < window]
        count = len(self._counters[key])

        if count >= limit:
            logger.warning("Rate limit exceeded for %s: %d/%d", platform, count, limit)
            return False

        if count >= int(limit * 0.8):
            logger.warning("Rate limit 80%% reached for %s: %d/%d", platform, count, limit)

        return True

    def record(self, platform: str):
        """Record an API call."""
        now = time.time()
        self._counters.setdefault(platform, []).append(now)

    def reset(self, platform: str):
        """Reset counters for a platform."""
        self._counters.pop(platform, None)


rate_limiter = RateLimiter()


# ── Circuit Breaker ──

class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker pattern for external API resilience.

    - CLOSED: normal operation
    - 5 consecutive failures → OPEN (block for open_timeout seconds)
    - After open_timeout → HALF_OPEN (allow 1 trial)
    - Trial success → CLOSED / failure → OPEN
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        open_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.open_timeout = open_timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.success_count = 0

    def _should_allow(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.open_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit %s: OPEN → HALF_OPEN", self.name)
                return True
            return False

        # HALF_OPEN: allow one trial
        return True

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit %s: HALF_OPEN → CLOSED", self.name)
        self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit %s: HALF_OPEN → OPEN", self.name)
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit %s: CLOSED → OPEN (failures=%d)",
                self.name, self.failure_count,
            )

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute func through the circuit breaker."""
        if not self._should_allow():
            raise CircuitOpenError(f"Circuit '{self.name}' is OPEN")

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure()
            raise exc

    def reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and blocking requests."""
    pass


# ── Retry with Exponential Backoff ──

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


async def retry_with_backoff(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (httpx.HTTPStatusError,),
    **kwargs: Any,
) -> Any:
    """Execute func with exponential backoff retry on retryable errors.

    Retries on: 429, 500, 502, 503, 504 status codes.
    Delay: backoff_base * (backoff_factor ** attempt)
        → 1s, 2s, 4s by default
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as exc:
            last_exc = exc
            # Check if it's a retryable HTTP status
            if isinstance(exc, httpx.HTTPStatusError):
                if exc.response.status_code not in RETRYABLE_STATUS_CODES:
                    raise  # Non-retryable status, fail immediately

            if attempt < max_retries:
                delay = backoff_base * (backoff_factor ** attempt)
                logger.warning(
                    "Retry %d/%d after %.1fs: %s",
                    attempt + 1, max_retries, delay, exc,
                )
                await asyncio.sleep(delay)
            else:
                logger.error("Max retries (%d) exceeded: %s", max_retries, exc)
                raise

    raise last_exc  # type: ignore[misc]


# ── Global circuit breakers (one per platform) ──

circuit_breakers: dict[str, CircuitBreaker] = {
    "instagram": CircuitBreaker("instagram"),
    "facebook": CircuitBreaker("facebook"),
    "youtube": CircuitBreaker("youtube"),
}


def get_circuit_breaker(platform: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a platform."""
    if platform not in circuit_breakers:
        circuit_breakers[platform] = CircuitBreaker(platform)
    return circuit_breakers[platform]
