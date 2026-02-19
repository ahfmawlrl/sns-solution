"""Publishing API - 6 endpoints."""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_role
from app.models.publishing_log import PublishingStatus
from app.models.user import User
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.publishing import (
    PublishingLogResponse,
    PublishNowRequest,
    ScheduleRequest,
)
from app.services import publishing_service

router = APIRouter()


# POST /publishing/schedule — admin, manager, operator
@router.post("/schedule", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def schedule_publish(
    body: ScheduleRequest,
    _caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    logs = await publishing_service.schedule_publish(
        db, body.content_id, body.platform_account_ids, body.scheduled_at,
    )
    return APIResponse(
        status="success",
        data=[PublishingLogResponse.model_validate(log).model_dump() for log in logs],
        message="Publishing scheduled",
    )


# POST /publishing/now — admin, manager, operator
@router.post("/now", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def publish_now(
    body: PublishNowRequest,
    _caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    logs = await publishing_service.publish_now(
        db, body.content_id, body.platform_account_ids,
    )
    return APIResponse(
        status="success",
        data=[PublishingLogResponse.model_validate(log).model_dump() for log in logs],
        message="Publishing started",
    )


# GET /publishing/queue — authenticated
@router.get("/queue", response_model=APIResponse)
async def get_queue(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logs, total = await publishing_service.get_queue(db, page, per_page)
    return APIResponse(
        status="success",
        data=[PublishingLogResponse.model_validate(log).model_dump() for log in logs],
        pagination=PaginationMeta(
            total=total, page=page, per_page=per_page,
            has_next=(page * per_page < total),
        ),
    )


# DELETE /publishing/{id}/cancel — admin, manager, operator
@router.delete("/{log_id}/cancel", response_model=APIResponse)
async def cancel_publish(
    log_id: uuid.UUID,
    _caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    log = await publishing_service.cancel_publish(db, log_id)
    return APIResponse(
        status="success",
        data=PublishingLogResponse.model_validate(log).model_dump(),
        message="Publishing cancelled",
    )


# GET /publishing/history — authenticated
@router.get("/history", response_model=APIResponse)
async def get_history(
    status_filter: PublishingStatus | None = Query(None, alias="status"),
    content_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logs, total = await publishing_service.get_history(
        db, status=status_filter, content_id=content_id, page=page, per_page=per_page,
    )
    return APIResponse(
        status="success",
        data=[PublishingLogResponse.model_validate(log).model_dump() for log in logs],
        pagination=PaginationMeta(
            total=total, page=page, per_page=per_page,
            has_next=(page * per_page < total),
        ),
    )


# POST /publishing/{id}/retry — admin, manager, operator
@router.post("/{log_id}/retry", response_model=APIResponse)
async def retry_publish(
    log_id: uuid.UUID,
    _caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    log = await publishing_service.retry_publish(db, log_id)
    return APIResponse(
        status="success",
        data=PublishingLogResponse.model_validate(log).model_dump(),
        message="Publishing retry initiated",
    )
