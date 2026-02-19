"""Notification business logic."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPriority, NotificationType
from app.schemas.notification import NotificationFilter


async def list_notifications(
    db: AsyncSession, user_id: uuid.UUID, filters: NotificationFilter,
) -> tuple[list[Notification], int]:
    query = select(Notification).where(Notification.user_id == user_id)

    if filters.type is not None:
        query = query.where(Notification.type == filters.type)
    if filters.is_read is not None:
        query = query.where(Notification.is_read == filters.is_read)
    if filters.priority is not None:
        query = query.where(Notification.priority == filters.priority)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (filters.page - 1) * filters.per_page
    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(filters.per_page)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    query = select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id,
        Notification.is_read == False,  # noqa: E712
    )
    return (await db.execute(query)).scalar() or 0


async def mark_read(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != user_id:
        return None
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    return notification


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = (
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    result = await db.execute(stmt)
    return result.rowcount
