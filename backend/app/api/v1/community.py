"""Community API - 8 endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_role
from app.models.comment import CommentStatus, Sentiment
from app.models.user import User
from app.schemas.comment import (
    CommentResponse,
    CommentStatusUpdate,
    FilterRuleCreate,
    FilterRuleResponse,
    FilterRuleUpdate,
    InboxFilter,
    ReplyRequest,
    SentimentStats,
)
from app.schemas.common import APIResponse, PaginationMeta
from app.services import community_service

router = APIRouter()


# GET /community/inbox — admin, manager, operator
@router.get("/inbox", response_model=APIResponse)
async def list_inbox(
    client_id: uuid.UUID | None = None,
    platform: str | None = None,
    sentiment: Sentiment | None = None,
    status_filter: CommentStatus | None = Query(None, alias="status"),
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    filters = InboxFilter(
        client_id=client_id, platform=platform, sentiment=sentiment,
        status=status_filter, search=search, page=page, per_page=per_page,
    )
    comments, total = await community_service.list_inbox(db, filters)
    return APIResponse(
        status="success",
        data=[CommentResponse.model_validate(c).model_dump() for c in comments],
        pagination=PaginationMeta(
            total=total, page=page, per_page=per_page,
            has_next=(page * per_page < total),
        ),
    )


# POST /community/{id}/reply — admin, manager, operator
@router.post("/{comment_id}/reply", response_model=APIResponse)
async def reply_to_comment(
    comment_id: uuid.UUID,
    body: ReplyRequest,
    caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    comment = await community_service.reply_to_comment(db, comment_id, body.message, caller)
    return APIResponse(
        status="success",
        data=CommentResponse.model_validate(comment).model_dump(),
        message="Reply sent",
    )


# PATCH /community/{id}/status — admin, manager, operator
@router.patch("/{comment_id}/status", response_model=APIResponse)
async def update_comment_status(
    comment_id: uuid.UUID,
    body: CommentStatusUpdate,
    _caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    comment = await community_service.update_comment_status(db, comment_id, body.status)
    return APIResponse(
        status="success",
        data=CommentResponse.model_validate(comment).model_dump(),
        message=f"Comment status changed to {body.status.value}",
    )


# GET /community/sentiment — authenticated
@router.get("/sentiment", response_model=APIResponse)
async def get_sentiment_stats(
    client_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stats = await community_service.get_sentiment_stats(db, client_id)
    return APIResponse(
        status="success",
        data=stats.model_dump(),
    )


# GET /community/filter-rules — admin, manager
@router.get("/filter-rules", response_model=APIResponse)
async def list_filter_rules(
    client_id: uuid.UUID | None = None,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    rules = await community_service.list_filter_rules(db, client_id)
    return APIResponse(
        status="success",
        data=[FilterRuleResponse.model_validate(r).model_dump() for r in rules],
    )


# POST /community/filter-rules — admin, manager
@router.post("/filter-rules", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_filter_rule(
    body: FilterRuleCreate,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    rule = await community_service.create_filter_rule(db, body)
    return APIResponse(
        status="success",
        data=FilterRuleResponse.model_validate(rule).model_dump(),
        message="Filter rule created",
    )


# PUT /community/filter-rules/{id} — admin, manager
@router.put("/filter-rules/{rule_id}", response_model=APIResponse)
async def update_filter_rule(
    rule_id: uuid.UUID,
    body: FilterRuleUpdate,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    rule = await community_service.update_filter_rule(db, rule_id, body)
    return APIResponse(
        status="success",
        data=FilterRuleResponse.model_validate(rule).model_dump(),
    )


# DELETE /community/filter-rules/{id} — admin, manager
@router.delete("/filter-rules/{rule_id}", response_model=APIResponse)
async def delete_filter_rule(
    rule_id: uuid.UUID,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    deleted = await community_service.delete_filter_rule(db, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Filter rule not found")
    return APIResponse(status="success", message="Filter rule deleted")
