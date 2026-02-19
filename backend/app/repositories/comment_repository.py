"""Comment data access layer."""
import uuid as _uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import CommentInbox, Sentiment


async def get_by_id(db: AsyncSession, comment_id: _uuid.UUID) -> CommentInbox | None:
    return (await db.execute(select(CommentInbox).where(CommentInbox.id == comment_id))).scalar_one_or_none()


async def list_comments(
    db: AsyncSession,
    *,
    platform_account_id: _uuid.UUID | None = None,
    sentiment: Sentiment | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[CommentInbox], int]:
    q = select(CommentInbox)
    count_q = select(func.count()).select_from(CommentInbox)

    if platform_account_id:
        q = q.where(CommentInbox.platform_account_id == platform_account_id)
        count_q = count_q.where(CommentInbox.platform_account_id == platform_account_id)
    if sentiment:
        q = q.where(CommentInbox.sentiment == sentiment)
        count_q = count_q.where(CommentInbox.sentiment == sentiment)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(q.offset(skip).limit(limit).order_by(CommentInbox.commented_at.desc()))).scalars().all()
    return list(rows), total


async def create(db: AsyncSession, comment: CommentInbox) -> CommentInbox:
    db.add(comment)
    await db.flush()
    return comment


async def update(db: AsyncSession, comment: CommentInbox) -> CommentInbox:
    await db.flush()
    return comment
