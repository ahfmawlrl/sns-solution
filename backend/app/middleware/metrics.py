"""Prometheus metrics endpoint and request tracking middleware.

Tracks: request count, latency, active connections, error rate.
"""
import time
import logging
from collections import defaultdict

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse, Response

logger = logging.getLogger(__name__)

# Simple in-memory metrics (replace with prometheus_client in production)
_metrics: dict[str, float] = defaultdict(float)
_histograms: dict[str, list[float]] = defaultdict(list)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request metrics."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        method = request.method
        path = request.url.path

        _metrics["http_requests_active"] += 1

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            _metrics["http_requests_errors_total"] += 1
            raise
        finally:
            duration = time.time() - start
            _metrics["http_requests_active"] -= 1
            _metrics["http_requests_total"] += 1
            _histograms["http_request_duration_seconds"].append(duration)

            key = f"http_requests_by_status_{status // 100}xx"
            _metrics[key] += 1

            # Log slow requests (>500ms)
            if duration > 0.5:
                logger.warning("slow_request", extra={
                    "method": method, "path": path,
                    "duration_ms": round(duration * 1000, 2),
                    "status": status,
                })

        return response


def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * p / 100)
    return sorted_data[min(idx, len(sorted_data) - 1)]


def setup_metrics(app: FastAPI) -> None:
    """Register the /metrics endpoint."""

    @app.get("/metrics", tags=["monitoring"], include_in_schema=False)
    async def metrics_endpoint():
        durations = _histograms.get("http_request_duration_seconds", [])
        lines = [
            "# HELP http_requests_total Total HTTP requests",
            "# TYPE http_requests_total counter",
            f'http_requests_total {_metrics["http_requests_total"]:.0f}',
            "",
            "# HELP http_requests_active Active HTTP requests",
            "# TYPE http_requests_active gauge",
            f'http_requests_active {_metrics["http_requests_active"]:.0f}',
            "",
            "# HELP http_requests_errors_total Total HTTP errors",
            "# TYPE http_requests_errors_total counter",
            f'http_requests_errors_total {_metrics["http_requests_errors_total"]:.0f}',
            "",
            "# HELP http_request_duration_seconds Request duration",
            "# TYPE http_request_duration_seconds summary",
            f'http_request_duration_seconds{{quantile="0.5"}} {_percentile(durations, 50):.6f}',
            f'http_request_duration_seconds{{quantile="0.9"}} {_percentile(durations, 90):.6f}',
            f'http_request_duration_seconds{{quantile="0.95"}} {_percentile(durations, 95):.6f}',
            f'http_request_duration_seconds{{quantile="0.99"}} {_percentile(durations, 99):.6f}',
            f"http_request_duration_seconds_count {len(durations)}",
            "",
            "# HELP http_requests_by_status HTTP requests by status class",
            "# TYPE http_requests_by_status counter",
            f'http_requests_by_status{{status="2xx"}} {_metrics["http_requests_by_status_2xx"]:.0f}',
            f'http_requests_by_status{{status="3xx"}} {_metrics["http_requests_by_status_3xx"]:.0f}',
            f'http_requests_by_status{{status="4xx"}} {_metrics["http_requests_by_status_4xx"]:.0f}',
            f'http_requests_by_status{{status="5xx"}} {_metrics["http_requests_by_status_5xx"]:.0f}',
        ]
        return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")
