"""Content business logic + workflow state machine."""
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog
from app.models.content import Content, ContentStatus
from app.models.content_approval import ContentApproval
from app.models.publishing_log import PublishingLog
from app.models.user import User, UserRole
from app.schemas.content import ContentCreate, ContentFilter, ContentUpdate, StatusChangeRequest

# --- Workflow transition rules ---

TRANSITIONS: dict[str, dict[str, set[str]]] = {
    # role -> { from_status -> set(allowed_to_statuses) }
    "operator": {
        "draft": {"review"},
    },
    "manager": {
        "review": {"client_review", "rejected"},
        "client_review": {"rejected"},
        "rejected": {"draft"},
    },
    "client": {
        "client_review": {"approved", "rejected"},
    },
    "admin": {
        # admin can do everything manager can
        "review": {"client_review", "rejected"},
        "client_review": {"rejected"},
        "rejected": {"draft"},
        "draft": {"review"},
    },
}


def validate_transition(
    role: str, from_status: ContentStatus, to_status: ContentStatus, is_urgent: bool = False,
) -> None:
    """Validate status transition for the given role."""
    if is_urgent and role in ("manager", "admin"):
        # Urgent: allow skipping to approved directly
        return

    allowed = TRANSITIONS.get(role, {}).get(from_status.value, set())
    if to_status.value not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Role '{role}' cannot transition from '{from_status.value}' to '{to_status.value}'",
        )


# --- CRUD ---

async def create_content(db: AsyncSession, data: ContentCreate, user: User) -> Content:
    content = Content(
        client_id=data.client_id,
        title=data.title,
        body=data.body,
        content_type=data.content_type,
        target_platforms=data.target_platforms,
        hashtags=data.hashtags,
        scheduled_at=data.scheduled_at,
        created_by=user.id,
    )
    db.add(content)
    await db.flush()

    # Audit log
    db.add(AuditLog(
        user_id=user.id,
        action=AuditAction.CREATE,
        entity_type="content",
        entity_id=content.id,
        changes={"title": data.title, "content_type": data.content_type.value},
    ))

    return content


async def get_content(db: AsyncSession, content_id: uuid.UUID) -> Content | None:
    return await db.get(Content, content_id)


async def list_contents(
    db: AsyncSession, filters: ContentFilter,
) -> tuple[list[Content], int]:
    query = select(Content)

    if filters.client_id:
        query = query.where(Content.client_id == filters.client_id)
    if filters.status:
        query = query.where(Content.status == filters.status)
    if filters.content_type:
        query = query.where(Content.content_type == filters.content_type)
    if filters.search:
        search = f"%{filters.search}%"
        query = query.where(Content.title.ilike(search))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (filters.page - 1) * filters.per_page
    query = query.order_by(Content.created_at.desc()).offset(offset).limit(filters.per_page)
    result = await db.execute(query)

    return list(result.scalars().all()), total


async def update_content(db: AsyncSession, content: Content, data: ContentUpdate, user: User) -> Content:
    changes = {}
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        old_value = getattr(content, key)
        setattr(content, key, value)
        changes[key] = {"from": str(old_value), "to": str(value)}

    if changes:
        db.add(AuditLog(
            user_id=user.id,
            action=AuditAction.UPDATE,
            entity_type="content",
            entity_id=content.id,
            changes=changes,
        ))

    return content


async def delete_content(db: AsyncSession, content: Content, user: User) -> bool:
    if content.status != ContentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft content can be deleted")
    db.add(AuditLog(
        user_id=user.id,
        action=AuditAction.DELETE,
        entity_type="content",
        entity_id=content.id,
        changes={"title": content.title},
    ))
    await db.delete(content)
    return True


async def change_status(
    db: AsyncSession, content: Content, req: StatusChangeRequest, user: User,
) -> Content:
    validate_transition(user.role.value, content.status, req.to_status, req.is_urgent)

    old_status = content.status
    content.status = req.to_status

    # Set approved_at/approved_by when transitioning to approved
    if req.to_status == ContentStatus.APPROVED:
        content.approved_at = datetime.now(timezone.utc)
        content.approved_by = user.id

    # Record approval history
    approval = ContentApproval(
        content_id=content.id,
        from_status=old_status,
        to_status=req.to_status,
        reviewer_id=user.id,
        comment=req.comment,
        is_urgent=req.is_urgent,
    )
    db.add(approval)

    # Audit log
    action = AuditAction.APPROVE if req.to_status == ContentStatus.APPROVED else (
        AuditAction.REJECT if req.to_status == ContentStatus.REJECTED else AuditAction.UPDATE
    )
    db.add(AuditLog(
        user_id=user.id,
        action=action,
        entity_type="content",
        entity_id=content.id,
        changes={"status": {"from": old_status.value, "to": req.to_status.value}},
    ))

    return content


# --- Calendar ---

async def get_calendar(
    db: AsyncSession, client_id: uuid.UUID | None, start: date, end: date, platform: str | None,
) -> list[Content]:
    query = select(Content).where(
        Content.scheduled_at.isnot(None),
        func.date(Content.scheduled_at) >= start,
        func.date(Content.scheduled_at) <= end,
    )
    if client_id:
        query = query.where(Content.client_id == client_id)
    query = query.order_by(Content.scheduled_at)
    result = await db.execute(query)
    return list(result.scalars().all())


# --- Approval history ---

async def list_approvals(db: AsyncSession, content_id: uuid.UUID) -> list[ContentApproval]:
    result = await db.execute(
        select(ContentApproval)
        .where(ContentApproval.content_id == content_id)
        .order_by(ContentApproval.created_at.desc())
    )
    return list(result.scalars().all())


# --- Publishing logs ---

async def list_publishing_logs(db: AsyncSession, content_id: uuid.UUID) -> list[PublishingLog]:
    result = await db.execute(
        select(PublishingLog)
        .where(PublishingLog.content_id == content_id)
        .order_by(PublishingLog.created_at.desc())
    )
    return list(result.scalars().all())


# --- S3 Presigned URL (stub) ---

def generate_upload_url(filename: str, content_type: str) -> tuple[str, str]:
    """Generate a presigned upload URL. Stub until S3/MinIO integration."""
    file_key = f"uploads/{uuid.uuid4().hex}/{filename}"
    upload_url = f"https://s3.example.com/{file_key}?presigned=stub"
    return upload_url, file_key
