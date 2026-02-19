"""Contents API - 10 endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_role
from app.models.content import ContentStatus, ContentType
from app.models.user import User
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.content import (
    ContentApprovalResponse,
    ContentCreate,
    ContentFilter,
    ContentResponse,
    ContentUpdate,
    PublishingLogResponse,
    StatusChangeRequest,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services import content_service

router = APIRouter()


# GET /contents
@router.get("", response_model=APIResponse)
async def list_contents(
    client_id: uuid.UUID | None = None,
    status_filter: ContentStatus | None = Query(None, alias="status"),
    content_type: ContentType | None = None,
    platform: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = ContentFilter(
        client_id=client_id, status=status_filter, content_type=content_type,
        platform=platform, search=search, page=page, per_page=per_page,
    )
    contents, total = await content_service.list_contents(db, filters)
    return APIResponse(
        status="success",
        data=[ContentResponse.model_validate(c).model_dump() for c in contents],
        pagination=PaginationMeta(
            total=total, page=page, per_page=per_page,
            has_next=(page * per_page < total),
        ),
    )


# POST /contents — admin, manager, operator
@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_content(
    body: ContentCreate,
    caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    content = await content_service.create_content(db, body, caller)
    return APIResponse(
        status="success",
        data=ContentResponse.model_validate(content).model_dump(),
        message="Content created",
    )


# GET /contents/calendar
@router.get("/calendar", response_model=APIResponse)
async def calendar_view(
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    client_id: uuid.UUID | None = None,
    platform: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as date_type
    start_date = date_type.fromisoformat(start)
    end_date = date_type.fromisoformat(end)
    contents = await content_service.get_calendar(db, client_id, start_date, end_date, platform)
    return APIResponse(
        status="success",
        data=[ContentResponse.model_validate(c).model_dump() for c in contents],
    )


# GET /contents/{id}
@router.get("/{content_id}", response_model=APIResponse)
async def get_content(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await content_service.get_content(db, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return APIResponse(
        status="success",
        data=ContentResponse.model_validate(content).model_dump(),
    )


# PUT /contents/{id} — admin, manager, operator
@router.put("/{content_id}", response_model=APIResponse)
async def update_content(
    content_id: uuid.UUID,
    body: ContentUpdate,
    caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    content = await content_service.get_content(db, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    updated = await content_service.update_content(db, content, body, caller)
    return APIResponse(
        status="success",
        data=ContentResponse.model_validate(updated).model_dump(),
    )


# DELETE /contents/{id} — admin, manager, operator (draft only)
@router.delete("/{content_id}", response_model=APIResponse)
async def delete_content(
    content_id: uuid.UUID,
    caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    content = await content_service.get_content(db, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    await content_service.delete_content(db, content, caller)
    return APIResponse(status="success", message="Content deleted")


# PATCH /contents/{id}/status — role-based
@router.patch("/{content_id}/status", response_model=APIResponse)
async def change_status(
    content_id: uuid.UUID,
    body: StatusChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await content_service.get_content(db, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    updated = await content_service.change_status(db, content, body, current_user)
    return APIResponse(
        status="success",
        data=ContentResponse.model_validate(updated).model_dump(),
        message=f"Status changed to {body.to_status.value}",
    )


# POST /contents/{id}/upload — admin, manager, operator
@router.post("/{content_id}/upload", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def get_upload_url(
    content_id: uuid.UUID,
    body: UploadUrlRequest,
    _caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    content = await content_service.get_content(db, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    upload_url, file_key = content_service.generate_upload_url(body.filename, body.content_type)
    return APIResponse(
        status="success",
        data=UploadUrlResponse(upload_url=upload_url, file_key=file_key).model_dump(),
        message="Upload URL generated",
    )


# GET /contents/{id}/approvals
@router.get("/{content_id}/approvals", response_model=APIResponse)
async def list_approvals(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    approvals = await content_service.list_approvals(db, content_id)
    return APIResponse(
        status="success",
        data=[ContentApprovalResponse.model_validate(a).model_dump() for a in approvals],
    )


# GET /contents/{id}/publishing-logs
@router.get("/{content_id}/publishing-logs", response_model=APIResponse)
async def list_publishing_logs(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logs = await content_service.list_publishing_logs(db, content_id)
    return APIResponse(
        status="success",
        data=[PublishingLogResponse.model_validate(log).model_dump() for log in logs],
    )
