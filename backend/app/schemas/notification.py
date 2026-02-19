"""Notification request/response schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.notification import NotificationPriority, NotificationType


class NotificationFilter(BaseModel):
    type: NotificationType | None = None
    is_read: bool | None = None
    priority: NotificationPriority | None = None
    page: int = 1
    per_page: int = 20


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    is_read: bool
    read_at: datetime | None = None
    priority: NotificationPriority
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    count: int


class WorkflowSettings(BaseModel):
    approval_steps: list[str] = ["review", "client_review"]
    auto_publish_on_approve: bool = False
    urgent_skip_enabled: bool = True
    notification_channels: dict = {}


class NotificationPreferences(BaseModel):
    email_enabled: bool = True
    slack_webhook_url: str | None = None
    kakao_enabled: bool = False
    crisis_alert: list[str] = ["email", "slack"]
    approval_request: list[str] = ["email"]
    publish_result: list[str] = ["email"]


class PlatformConnectionStatus(BaseModel):
    platform: str
    account_name: str
    is_connected: bool
    token_expires_at: datetime | None = None


class PlatformTestRequest(BaseModel):
    platform_account_id: uuid.UUID
