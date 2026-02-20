"""Settings API - 7 endpoints."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db, require_role
from app.integrations.meta.client import MetaGraphClient
from app.models.audit_log import AuditLog
from app.models.platform_account import Platform, PlatformAccount
from app.models.user import User
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.notification import (
    NotificationPreferences,
    PlatformConnectionStatus,
    PlatformTestRequest,
    WorkflowSettings,
)
from app.utils.encryption import TokenEncryptor

router = APIRouter()

# In-memory settings store (will be Redis/DB in production)
_workflow_settings = WorkflowSettings()
_user_notification_prefs: dict[str, NotificationPreferences] = {}


# GET /settings/platform-connections — admin, manager
@router.get("/platform-connections", response_model=APIResponse)
async def list_platform_connections(
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PlatformAccount))
    accounts = list(result.scalars().all())
    data = [
        PlatformConnectionStatus(
            platform=a.platform.value,
            account_name=a.account_name,
            is_connected=a.is_connected,
            token_expires_at=a.token_expires_at,
        ).model_dump()
        for a in accounts
    ]
    return APIResponse(status="success", data=data)


# POST /settings/platform-connections/test — admin, manager
@router.post("/platform-connections/test", response_model=APIResponse)
async def test_platform_connection(
    body: PlatformTestRequest,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(PlatformAccount, body.platform_account_id)
    if not account:
        return APIResponse(status="error", message="Platform account not found")

    # ── Decrypt stored token ─────────────────────────────────────────────────
    if not settings.ENCRYPTION_KEY:
        return APIResponse(status="error", message="ENCRYPTION_KEY is not configured on the server")
    try:
        encryptor = TokenEncryptor(settings.ENCRYPTION_KEY)
        token = encryptor.decrypt(account.access_token)
    except Exception:
        return APIResponse(status="error", message="Token decryption failed — re-register the access token")

    # ── Call the platform API ────────────────────────────────────────────────
    me: dict = {}
    connected = False
    error_detail: str | None = None

    if account.platform.value in (Platform.INSTAGRAM.value, Platform.FACEBOOK.value):
        try:
            async with MetaGraphClient(token) as client:
                me = await client.get_me()
            connected = "id" in me
        except Exception as exc:
            connected = False
            error_detail = str(exc)
    else:
        # YouTube and other platforms: fall back to stored flag until implemented
        connected = account.is_connected
        me = {"note": "Live test not yet implemented for this platform"}

    # ── Sync is_connected to DB ──────────────────────────────────────────────
    account.is_connected = connected
    await db.commit()

    response_data: dict = {
        "platform": account.platform.value,
        "connected": connected,
        "account_info": me if connected else None,
    }
    if error_detail:
        response_data["error_detail"] = error_detail

    return APIResponse(
        status="success" if connected else "error",
        data=response_data,
        message="Connection test passed" if connected else "Connection test failed",
    )


# GET /settings/workflows — admin, manager
@router.get("/workflows", response_model=APIResponse)
async def get_workflow_settings(
    _caller: User = require_role("admin", "manager"),
):
    return APIResponse(status="success", data=_workflow_settings.model_dump())


# PUT /settings/workflows — admin
@router.put("/workflows", response_model=APIResponse)
async def update_workflow_settings(
    body: WorkflowSettings,
    _caller: User = require_role("admin"),
):
    global _workflow_settings
    _workflow_settings = body
    return APIResponse(
        status="success",
        data=_workflow_settings.model_dump(),
        message="Workflow settings updated",
    )


# GET /settings/notification-preferences — authenticated
@router.get("/notification-preferences", response_model=APIResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
):
    prefs = _user_notification_prefs.get(str(current_user.id), NotificationPreferences())
    return APIResponse(status="success", data=prefs.model_dump())


# PUT /settings/notification-preferences — authenticated
@router.put("/notification-preferences", response_model=APIResponse)
async def update_notification_preferences(
    body: NotificationPreferences,
    current_user: User = Depends(get_current_user),
):
    _user_notification_prefs[str(current_user.id)] = body
    return APIResponse(
        status="success",
        data=body.model_dump(),
        message="Notification preferences updated",
    )


# GET /settings/audit-logs — admin, manager
@router.get("/audit-logs", response_model=APIResponse)
async def list_audit_logs(
    entity_type: str | None = None,
    user_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    query = select(AuditLog)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    logs = list(result.scalars().all())

    data = [
        {
            "id": str(log.id),
            "user_id": str(log.user_id),
            "action": log.action.value,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "changes": log.changes,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    return APIResponse(
        status="success",
        data=data,
        pagination=PaginationMeta(
            total=total, page=page, per_page=per_page,
            has_next=(page * per_page < total),
        ),
    )
