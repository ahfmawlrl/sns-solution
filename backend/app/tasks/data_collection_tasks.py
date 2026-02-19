"""Data collection tasks — MEDIUM queue.

Handles comment sync, analytics collection, and token refresh.
"""
import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.data_collection_tasks.sync_comments")
def sync_comments():
    """Periodic task (every 5 min): sync comments from all active platform accounts.

    For each active account:
        1. Call platform API to fetch recent comments
        2. Upsert into comments_inbox (by platform_comment_id)
        3. Chain sentiment analysis for new comments
        4. Push new_comment WebSocket event
    """
    from sqlalchemy import select
    from app.database import async_session_factory
    from app.models.platform_account import PlatformAccount
    import asyncio

    async def _sync():
        async with async_session_factory() as db:
            result = await db.execute(
                select(PlatformAccount).where(PlatformAccount.is_connected.is_(True))
            )
            accounts = result.scalars().all()

            for account in accounts:
                try:
                    # Placeholder: actual API call in STEP 16-17
                    # Would call Meta Graph API or YouTube Data API here
                    logger.debug(
                        "Syncing comments for %s account: %s",
                        account.platform.value,
                        account.account_name,
                    )
                except Exception:
                    logger.exception(
                        "Failed to sync comments for account %s", account.id
                    )

            logger.info("Comment sync completed for %d accounts", len(accounts))

    try:
        asyncio.get_event_loop().run_until_complete(_sync())
    except RuntimeError:
        asyncio.run(_sync())


@celery_app.task(name="app.tasks.data_collection_tasks.collect_analytics")
def collect_analytics():
    """Periodic task (every 1 hour): collect insights/analytics from platform APIs.

    For each active account:
        1. Call insights API
        2. Upsert analytics_snapshots (daily granularity)
        3. Update Redis cache for dashboard KPIs
    """
    from sqlalchemy import select
    from app.database import async_session_factory
    from app.models.platform_account import PlatformAccount
    import asyncio

    async def _collect():
        async with async_session_factory() as db:
            result = await db.execute(
                select(PlatformAccount).where(PlatformAccount.is_connected.is_(True))
            )
            accounts = result.scalars().all()

            for account in accounts:
                try:
                    # Placeholder: actual API call in STEP 16-17
                    logger.debug(
                        "Collecting analytics for %s account: %s",
                        account.platform.value,
                        account.account_name,
                    )
                except Exception:
                    logger.exception(
                        "Failed to collect analytics for account %s", account.id
                    )

            logger.info("Analytics collection completed for %d accounts", len(accounts))

    try:
        asyncio.get_event_loop().run_until_complete(_collect())
    except RuntimeError:
        asyncio.run(_collect())


@celery_app.task(name="app.tasks.data_collection_tasks.refresh_expiring_tokens")
def refresh_expiring_tokens():
    """Periodic task (every 1 hour): refresh tokens expiring within 24 hours.

    For each account with token_expires_at < now + 24h:
        1. Use refresh_token to get new access_token
        2. Update encrypted access_token + token_expires_at
        3. On failure: send notification to admin (re-auth required)
    """
    from sqlalchemy import select, update
    from app.database import async_session_factory
    from app.models.platform_account import PlatformAccount
    import asyncio

    async def _refresh():
        async with async_session_factory() as db:
            threshold = datetime.now(timezone.utc) + timedelta(hours=24)
            result = await db.execute(
                select(PlatformAccount).where(
                    PlatformAccount.is_connected.is_(True),
                    PlatformAccount.token_expires_at.isnot(None),
                    PlatformAccount.token_expires_at < threshold,
                )
            )
            expiring = result.scalars().all()

            refreshed = 0
            failed = 0
            for account in expiring:
                try:
                    # Placeholder: actual OAuth refresh in STEP 16-17
                    logger.info(
                        "Would refresh token for %s account: %s",
                        account.platform.value,
                        account.account_name,
                    )
                    refreshed += 1
                except Exception:
                    logger.exception(
                        "Token refresh failed for account %s", account.id
                    )
                    failed += 1

            logger.info(
                "Token refresh: %d refreshed, %d failed, out of %d expiring",
                refreshed, failed, len(expiring),
            )

    try:
        asyncio.get_event_loop().run_until_complete(_refresh())
    except RuntimeError:
        asyncio.run(_refresh())
