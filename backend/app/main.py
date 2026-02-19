"""SNS Solution Backend - FastAPI Entry Point."""
import sys

# asyncpg is incompatible with Windows ProactorEventLoop (default on Windows).
# Must be set before any asyncio usage.
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI

from app.config import settings
from app.database import engine
from app.middleware.cors import setup_cors, setup_cookie_security
from app.middleware.error_handler import setup_error_handlers
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.metrics import MetricsMiddleware, setup_metrics
from app.api.v1 import auth as auth_router
from app.api.v1 import users as users_router
from app.api.v1 import clients as clients_router
from app.api.v1 import contents as contents_router
from app.api.v1 import publishing as publishing_router
from app.api.v1 import community as community_router
from app.api.v1 import analytics as analytics_router
from app.api.v1 import notifications as notifications_router
from app.api.v1 import settings as settings_router
from app.api.v1 import ai_tools as ai_tools_router
from app.api import websocket as ws_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("startup", env=settings.APP_ENV)
    # Sentry init
    if settings.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1 if settings.APP_ENV == "production" else 1.0,
            environment=settings.APP_ENV,
        )
    # Start Redis Pub/Sub listener for WebSocket cross-instance support
    from app.api.websocket import manager as ws_manager
    await ws_manager.start_redis_listener()

    yield

    # Shutdown: stop Redis listener, close Redis, dispose DB engine
    await ws_manager.stop_redis_listener()
    from app.utils.redis_client import close_redis
    await close_redis()
    await engine.dispose()
    logger.info("shutdown")


def create_app() -> FastAPI:
    application = FastAPI(
        title="SNS Solution API",
        description="SNS Operation Management Integrated Solution",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Middleware (order matters: last added = first executed)
    setup_cors(application)
    setup_cookie_security(application)
    setup_error_handlers(application)
    application.add_middleware(LoggingMiddleware)
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(AuditMiddleware)
    application.add_middleware(MetricsMiddleware)

    # Prometheus metrics endpoint
    setup_metrics(application)

    # API Routers
    application.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Auth"])
    application.include_router(users_router.router, prefix="/api/v1/users", tags=["Users"])
    application.include_router(clients_router.router, prefix="/api/v1/clients", tags=["Clients"])
    application.include_router(contents_router.router, prefix="/api/v1/contents", tags=["Contents"])
    application.include_router(publishing_router.router, prefix="/api/v1/publishing", tags=["Publishing"])
    application.include_router(community_router.router, prefix="/api/v1/community", tags=["Community"])
    application.include_router(analytics_router.router, prefix="/api/v1/analytics", tags=["Analytics"])
    application.include_router(notifications_router.router, prefix="/api/v1/notifications", tags=["Notifications"])
    application.include_router(settings_router.router, prefix="/api/v1/settings", tags=["Settings"])
    application.include_router(ai_tools_router.router, prefix="/api/v1/ai", tags=["AI Tools"])
    application.include_router(ws_router.router, tags=["WebSocket"])

    # Health check
    @application.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
