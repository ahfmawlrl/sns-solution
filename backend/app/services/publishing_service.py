"""Publishing business logic."""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content, ContentStatus
from app.models.publishing_log import PublishingLog, PublishingStatus


async def schedule_publish(
    db: AsyncSession,
    content_id: uuid.UUID,
    platform_account_ids: list[uuid.UUID],
    scheduled_at: datetime,
) -> list[PublishingLog]:
    """Create scheduled publishing logs for each platform account."""
    content = await db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.status != ContentStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Content must be approved before publishing")

    logs = []
    for account_id in platform_account_ids:
        log = PublishingLog(
            content_id=content_id,
            platform_account_id=account_id,
            status=PublishingStatus.PENDING,
            scheduled_at=scheduled_at,
        )
        db.add(log)
        logs.append(log)

    await db.flush()
    return logs


async def publish_now(
    db: AsyncSession,
    content_id: uuid.UUID,
    platform_account_ids: list[uuid.UUID],
) -> list[PublishingLog]:
    """Create immediate publishing logs (Celery integration in STEP 14)."""
    content = await db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.status != ContentStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Content must be approved before publishing")

    logs = []
    for account_id in platform_account_ids:
        log = PublishingLog(
            content_id=content_id,
            platform_account_id=account_id,
            status=PublishingStatus.PUBLISHING,
        )
        db.add(log)
        logs.append(log)

    await db.flush()
    return logs


async def get_queue(
    db: AsyncSession, page: int = 1, per_page: int = 20,
) -> tuple[list[PublishingLog], int]:
    """Get pending/publishing logs."""
    query = select(PublishingLog).where(
        PublishingLog.status.in_([PublishingStatus.PENDING, PublishingStatus.PUBLISHING])
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(PublishingLog.scheduled_at.asc().nullsfirst()).offset(offset).limit(per_page)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def cancel_publish(db: AsyncSession, log_id: uuid.UUID) -> PublishingLog:
    """Cancel a pending publishing log."""
    log = await db.get(PublishingLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Publishing log not found")
    if log.status != PublishingStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending publishing can be cancelled")
    log.status = PublishingStatus.CANCELLED
    return log


async def get_history(
    db: AsyncSession,
    status: PublishingStatus | None = None,
    content_id: uuid.UUID | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[PublishingLog], int]:
    """Get publishing history with optional filters."""
    query = select(PublishingLog)
    if status:
        query = query.where(PublishingLog.status == status)
    if content_id:
        query = query.where(PublishingLog.content_id == content_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(PublishingLog.created_at.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def retry_publish(db: AsyncSession, log_id: uuid.UUID) -> PublishingLog:
    """Retry a failed publishing log."""
    log = await db.get(PublishingLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Publishing log not found")
    if log.status != PublishingStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed publishing can be retried")
    log.status = PublishingStatus.PUBLISHING
    log.retry_count += 1
    log.error_message = None
    return log
