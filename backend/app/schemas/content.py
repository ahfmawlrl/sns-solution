"""Content request/response schemas."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.content import ContentStatus, ContentType


class ContentCreate(BaseModel):
    client_id: uuid.UUID
    title: str = Field(max_length=500)
    body: str | None = None
    content_type: ContentType
    target_platforms: list[str]
    hashtags: list[str] | None = None
    scheduled_at: datetime | None = None


class ContentUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    body: str | None = None
    content_type: ContentType | None = None
    target_platforms: list[str] | None = None
    hashtags: list[str] | None = None
    scheduled_at: datetime | None = None


class StatusChangeRequest(BaseModel):
    to_status: ContentStatus
    comment: str | None = None
    is_urgent: bool = False


class ContentFilter(BaseModel):
    client_id: uuid.UUID | None = None
    status: ContentStatus | None = None
    content_type: ContentType | None = None
    platform: str | None = None
    search: str | None = None
    page: int = 1
    per_page: int = 20


class CalendarQuery(BaseModel):
    client_id: uuid.UUID | None = None
    start: date
    end: date
    platform: str | None = None


class ContentResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    body: str | None = None
    content_type: ContentType
    status: ContentStatus
    media_urls: dict | None = None
    hashtags: list[str] | None = None
    target_platforms: list[str]
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by: uuid.UUID | None = None
    ai_metadata: dict | None = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentApprovalResponse(BaseModel):
    id: uuid.UUID
    content_id: uuid.UUID
    from_status: ContentStatus
    to_status: ContentStatus
    reviewer_id: uuid.UUID
    comment: str | None = None
    is_urgent: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PublishingLogResponse(BaseModel):
    id: uuid.UUID
    content_id: uuid.UUID
    platform_account_id: uuid.UUID
    status: str
    platform_post_id: str | None = None
    platform_post_url: str | None = None
    error_message: str | None = None
    retry_count: int
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str  # MIME type


class UploadUrlResponse(BaseModel):
    upload_url: str
    file_key: str
