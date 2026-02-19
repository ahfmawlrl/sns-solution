"""Client data access layer."""
import uuid as _uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client


async def get_by_id(db: AsyncSession, client_id: _uuid.UUID) -> Client | None:
    return (await db.execute(select(Client).where(Client.id == client_id))).scalar_one_or_none()


async def list_clients(
    db: AsyncSession,
    *,
    industry: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Client], int]:
    q = select(Client)
    count_q = select(func.count()).select_from(Client)

    if industry:
        q = q.where(Client.industry == industry)
        count_q = count_q.where(Client.industry == industry)
    if search:
        pattern = f"%{search}%"
        q = q.where(Client.name.ilike(pattern))
        count_q = count_q.where(Client.name.ilike(pattern))

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(q.offset(skip).limit(limit).order_by(Client.created_at.desc()))).scalars().all()
    return list(rows), total


async def create(db: AsyncSession, client: Client) -> Client:
    db.add(client)
    await db.flush()
    return client


async def update(db: AsyncSession, client: Client) -> Client:
    await db.flush()
    return client
