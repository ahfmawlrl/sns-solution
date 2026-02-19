"""Content data access layer."""
import uuid as _uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content, ContentStatus


async def get_by_id(db: AsyncSession, content_id: _uuid.UUID) -> Content | None:
    return (await db.execute(select(Content).where(Content.id == content_id))).scalar_one_or_none()


async def list_contents(
    db: AsyncSession,
    *,
    client_id: _uuid.UUID | None = None,
    status: ContentStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Content], int]:
    q = select(Content)
    count_q = select(func.count()).select_from(Content)

    if client_id:
        q = q.where(Content.client_id == client_id)
        count_q = count_q.where(Content.client_id == client_id)
    if status:
        q = q.where(Content.status == status)
        count_q = count_q.where(Content.status == status)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(q.offset(skip).limit(limit).order_by(Content.created_at.desc()))).scalars().all()
    return list(rows), total


async def create(db: AsyncSession, content: Content) -> Content:
    db.add(content)
    await db.flush()
    return content


async def update(db: AsyncSession, content: Content) -> Content:
    await db.flush()
    return content


async def delete(db: AsyncSession, content: Content) -> None:
    await db.delete(content)
    await db.flush()
