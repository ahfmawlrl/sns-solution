"""Community / comment management business logic."""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import CommentInbox, CommentStatus, Sentiment
from app.models.filter_rule import FilterRule
from app.models.user import User
from app.schemas.comment import (
    CommentStatusUpdate,
    FilterRuleCreate,
    FilterRuleUpdate,
    InboxFilter,
    SentimentStats,
)


# --- Inbox ---

async def list_inbox(
    db: AsyncSession, filters: InboxFilter,
) -> tuple[list[CommentInbox], int]:
    query = select(CommentInbox)

    if filters.sentiment:
        query = query.where(CommentInbox.sentiment == filters.sentiment)
    if filters.status:
        query = query.where(CommentInbox.status == filters.status)
    if filters.search:
        search = f"%{filters.search}%"
        query = query.where(CommentInbox.message.ilike(search))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (filters.page - 1) * filters.per_page
    query = query.order_by(CommentInbox.commented_at.desc()).offset(offset).limit(filters.per_page)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def reply_to_comment(
    db: AsyncSession, comment_id: uuid.UUID, message: str, user: User,
) -> CommentInbox:
    comment = await db.get(CommentInbox, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.status = CommentStatus.REPLIED
    comment.replied_at = datetime.now(timezone.utc)
    comment.replied_by = user.id
    # In real integration, this would post via SNS API
    return comment


async def update_comment_status(
    db: AsyncSession, comment_id: uuid.UUID, new_status: CommentStatus,
) -> CommentInbox:
    comment = await db.get(CommentInbox, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.status = new_status
    return comment


async def get_sentiment_stats(db: AsyncSession, client_id: uuid.UUID | None = None) -> SentimentStats:
    stats = SentimentStats()
    for sentiment_val in Sentiment:
        query = select(func.count()).select_from(CommentInbox).where(
            CommentInbox.sentiment == sentiment_val
        )
        count = (await db.execute(query)).scalar() or 0
        setattr(stats, sentiment_val.value, count)
    stats.total = stats.positive + stats.neutral + stats.negative + stats.crisis
    return stats


# --- Filter Rules ---

async def list_filter_rules(db: AsyncSession, client_id: uuid.UUID | None = None) -> list[FilterRule]:
    query = select(FilterRule)
    if client_id:
        query = query.where(FilterRule.client_id == client_id)
    query = query.order_by(FilterRule.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_filter_rule(db: AsyncSession, data: FilterRuleCreate) -> FilterRule:
    rule = FilterRule(
        client_id=data.client_id,
        rule_type=data.rule_type,
        value=data.value,
        action=data.action,
        is_active=data.is_active,
    )
    db.add(rule)
    await db.flush()
    return rule


async def update_filter_rule(db: AsyncSession, rule_id: uuid.UUID, data: FilterRuleUpdate) -> FilterRule:
    rule = await db.get(FilterRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Filter rule not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)
    return rule


async def delete_filter_rule(db: AsyncSession, rule_id: uuid.UUID) -> bool:
    rule = await db.get(FilterRule, rule_id)
    if not rule:
        return False
    await db.delete(rule)
    return True
