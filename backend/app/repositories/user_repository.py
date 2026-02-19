"""User data access layer."""
import uuid as _uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


async def get_by_id(db: AsyncSession, user_id: _uuid.UUID) -> User | None:
    return (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    return (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()


async def list_users(
    db: AsyncSession,
    *,
    role: UserRole | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[User], int]:
    q = select(User)
    count_q = select(func.count()).select_from(User)

    if role:
        q = q.where(User.role == role)
        count_q = count_q.where(User.role == role)
    if search:
        pattern = f"%{search}%"
        cond = or_(User.name.ilike(pattern), User.email.ilike(pattern))
        q = q.where(cond)
        count_q = count_q.where(cond)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(q.offset(skip).limit(limit).order_by(User.created_at.desc()))).scalars().all()
    return list(rows), total


async def create(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.flush()
    return user


async def update(db: AsyncSession, user: User) -> User:
    await db.flush()
    return user
