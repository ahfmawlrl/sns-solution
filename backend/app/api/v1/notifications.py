"""Notifications API - 4 endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.notification import NotificationPriority, NotificationType
from app.models.user import User
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.notification import NotificationFilter, NotificationResponse, UnreadCountResponse
from app.services import notification_service

router = APIRouter()


# GET /notifications
@router.get("", response_model=APIResponse)
async def list_notifications(
    type_filter: NotificationType | None = Query(None, alias="type"),
    is_read: bool | None = None,
    priority: NotificationPriority | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = NotificationFilter(
        type=type_filter, is_read=is_read, priority=priority,
        page=page, per_page=per_page,
    )
    notifications, total = await notification_service.list_notifications(
        db, current_user.id, filters,
    )
    return APIResponse(
        status="success",
        data=[NotificationResponse.model_validate(n).model_dump() for n in notifications],
        pagination=PaginationMeta(
            total=total, page=page, per_page=per_page,
            has_next=(page * per_page < total),
        ),
    )


# GET /notifications/unread-count
@router.get("/unread-count", response_model=APIResponse)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.get_unread_count(db, current_user.id)
    return APIResponse(
        status="success",
        data=UnreadCountResponse(count=count).model_dump(),
    )


# PATCH /notifications/{id}/read
@router.patch("/{notification_id}/read", response_model=APIResponse)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notification = await notification_service.mark_read(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return APIResponse(
        status="success",
        data=NotificationResponse.model_validate(notification).model_dump(),
        message="Marked as read",
    )


# PATCH /notifications/read-all
@router.patch("/read-all", response_model=APIResponse)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.mark_all_read(db, current_user.id)
    return APIResponse(
        status="success",
        data={"updated_count": count},
        message=f"{count} notifications marked as read",
    )
