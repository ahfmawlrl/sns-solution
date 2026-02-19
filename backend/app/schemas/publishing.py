"""Publishing request/response schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.publishing_log import PublishingStatus


class ScheduleRequest(BaseModel):
    content_id: uuid.UUID
    platform_account_ids: list[uuid.UUID]
    scheduled_at: datetime


class PublishNowRequest(BaseModel):
    content_id: uuid.UUID
    platform_account_ids: list[uuid.UUID]


class PublishingQueueFilter(BaseModel):
    status: PublishingStatus | None = None
    platform: str | None = None
    page: int = 1
    per_page: int = 20


class PublishingHistoryFilter(BaseModel):
    status: PublishingStatus | None = None
    content_id: uuid.UUID | None = None
    page: int = 1
    per_page: int = 20


class PublishingLogResponse(BaseModel):
    id: uuid.UUID
    content_id: uuid.UUID
    platform_account_id: uuid.UUID
    status: PublishingStatus
    platform_post_id: str | None = None
    platform_post_url: str | None = None
    error_message: str | None = None
    retry_count: int
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    celery_task_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
