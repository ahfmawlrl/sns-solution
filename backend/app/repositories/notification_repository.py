"""Notification data access layer."""
import uuid as _uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def get_by_id(db: AsyncSession, notification_id: _uuid.UUID) -> Notification | None:
    return (await db.execute(select(Notification).where(Notification.id == notification_id))).scalar_one_or_none()


async def list_for_user(
    db: AsyncSession,
    user_id: _uuid.UUID,
    *,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Notification], int]:
    q = select(Notification).where(Notification.user_id == user_id)
    count_q = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)

    if unread_only:
        q = q.where(Notification.is_read.is_(False))
        count_q = count_q.where(Notification.is_read.is_(False))

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(q.offset(skip).limit(limit).order_by(Notification.created_at.desc()))).scalars().all()
    return list(rows), total


async def unread_count(db: AsyncSession, user_id: _uuid.UUID) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
    ).scalar() or 0


async def mark_all_read(db: AsyncSession, user_id: _uuid.UUID) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.flush()
    return result.rowcount


async def create(db: AsyncSession, notification: Notification) -> Notification:
    db.add(notification)
    await db.flush()
    return notification
