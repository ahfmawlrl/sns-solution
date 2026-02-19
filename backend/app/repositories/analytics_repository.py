"""Analytics data access layer."""
import uuid as _uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsSnapshot


async def get_latest(db: AsyncSession, client_id: _uuid.UUID) -> AnalyticsSnapshot | None:
    return (
        await db.execute(
            select(AnalyticsSnapshot)
            .where(AnalyticsSnapshot.client_id == client_id)
            .order_by(AnalyticsSnapshot.snapshot_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def list_snapshots(
    db: AsyncSession,
    *,
    client_id: _uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[AnalyticsSnapshot], int]:
    q = select(AnalyticsSnapshot)
    count_q = select(func.count()).select_from(AnalyticsSnapshot)

    if client_id:
        q = q.where(AnalyticsSnapshot.client_id == client_id)
        count_q = count_q.where(AnalyticsSnapshot.client_id == client_id)
    if start_date:
        q = q.where(AnalyticsSnapshot.snapshot_date >= start_date)
        count_q = count_q.where(AnalyticsSnapshot.snapshot_date >= start_date)
    if end_date:
        q = q.where(AnalyticsSnapshot.snapshot_date <= end_date)
        count_q = count_q.where(AnalyticsSnapshot.snapshot_date <= end_date)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        await db.execute(q.offset(skip).limit(limit).order_by(AnalyticsSnapshot.snapshot_date.desc()))
    ).scalars().all()
    return list(rows), total


async def create(db: AsyncSession, snapshot: AnalyticsSnapshot) -> AnalyticsSnapshot:
    db.add(snapshot)
    await db.flush()
    return snapshot
