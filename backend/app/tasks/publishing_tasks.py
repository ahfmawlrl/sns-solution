"""Publishing tasks — CRITICAL queue.

Handles scheduled/immediate SNS publishing and periodic scan for due posts.
"""
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.publishing_tasks.publish_to_platform", max_retries=3, default_retry_delay=30)
def publish_to_platform(self, publishing_log_id: str, content_id: str, platform_account_id: str):
    """Publish content to a specific platform account.

    Steps:
        1. Load content + account from DB
        2. Call platform API (Meta / YouTube)
        3. Update publishing_log status (success / failed)
        4. On success: set content.published_at
        5. Push WebSocket notification
        6. On failure: retry with backoff, increment retry_count
    """
    from sqlalchemy import select, update
    from app.database import async_session_factory
    from app.models.publishing_log import PublishingLog, PublishingStatus
    from app.models.content import Content
    from app.models.platform_account import PlatformAccount
    import asyncio

    async def _publish():
        async with async_session_factory() as db:
            log = (await db.execute(
                select(PublishingLog).where(PublishingLog.id == publishing_log_id)
            )).scalar_one_or_none()

            if not log:
                logger.error("PublishingLog %s not found", publishing_log_id)
                return

            content = (await db.execute(
                select(Content).where(Content.id == content_id)
            )).scalar_one_or_none()

            account = (await db.execute(
                select(PlatformAccount).where(PlatformAccount.id == platform_account_id)
            )).scalar_one_or_none()

            if not content or not account:
                await db.execute(
                    update(PublishingLog)
                    .where(PublishingLog.id == publishing_log_id)
                    .values(status=PublishingStatus.FAILED, error_message="Content or account not found")
                )
                await db.commit()
                return

            # Mark as publishing
            await db.execute(
                update(PublishingLog)
                .where(PublishingLog.id == publishing_log_id)
                .values(status=PublishingStatus.PUBLISHING)
            )
            await db.commit()

            try:
                # Platform API call placeholder
                # In STEP 16-17, actual Meta/YouTube integration will be added
                platform_post_id = f"mock_{account.platform.value}_{publishing_log_id[:8]}"
                platform_post_url = f"https://{account.platform.value}.com/p/{platform_post_id}"

                now = datetime.now(timezone.utc)
                await db.execute(
                    update(PublishingLog)
                    .where(PublishingLog.id == publishing_log_id)
                    .values(
                        status=PublishingStatus.SUCCESS,
                        platform_post_id=platform_post_id,
                        platform_post_url=platform_post_url,
                        published_at=now,
                    )
                )

                # Update content published_at
                from app.models.content import ContentStatus
                await db.execute(
                    update(Content)
                    .where(Content.id == content_id)
                    .values(published_at=now, status=ContentStatus.PUBLISHED)
                )
                await db.commit()
                logger.info("Published content %s to %s", content_id, account.platform.value)

                # Push WebSocket notification via Redis Pub/Sub
                try:
                    import redis as sync_redis
                    from app.config import settings
                    r = sync_redis.from_url(settings.REDIS_URL)
                    import json
                    r.publish(f"ws:user:{str(content.created_by)}", json.dumps({
                        "type": "publish_result",
                        "data": {
                            "content_id": str(content_id),
                            "status": "success",
                            "platform": account.platform.value,
                            "message": f"Content published to {account.platform.value}",
                        }
                    }))
                    r.close()
                except Exception:
                    logger.warning("Failed to push WS notification for publish")

            except Exception as exc:
                await db.rollback()
                await db.execute(
                    update(PublishingLog)
                    .where(PublishingLog.id == publishing_log_id)
                    .values(
                        status=PublishingStatus.FAILED,
                        error_message=str(exc),
                        retry_count=PublishingLog.retry_count + 1,
                    )
                )
                await db.commit()
                logger.error("Publish failed for %s: %s", publishing_log_id, exc)
                raise self.retry(exc=exc)

    asyncio.get_event_loop().run_until_complete(_publish())


@celery_app.task(name="app.tasks.publishing_tasks.scan_scheduled_posts")
def scan_scheduled_posts():
    """Periodic task (every 1 min): find approved content with scheduled_at <= now and trigger publishing."""
    from sqlalchemy import select
    from app.database import async_session_factory
    from app.models.publishing_log import PublishingLog, PublishingStatus
    import asyncio

    async def _scan():
        async with async_session_factory() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(PublishingLog).where(
                    PublishingLog.status == PublishingStatus.PENDING,
                    PublishingLog.scheduled_at <= now,
                )
            )
            due_logs = result.scalars().all()

            for log in due_logs:
                publish_to_platform.delay(
                    str(log.id),
                    str(log.content_id),
                    str(log.platform_account_id),
                )
                logger.info("Dispatched scheduled publish for log %s", log.id)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(asyncio.run, _scan()).result()
        else:
            loop.run_until_complete(_scan())
    except RuntimeError:
        asyncio.run(_scan())
