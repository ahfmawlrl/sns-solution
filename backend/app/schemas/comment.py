"""Comment/Community request/response schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.comment import CommentStatus, Sentiment
from app.models.filter_rule import FilterAction, RuleType


class InboxFilter(BaseModel):
    client_id: uuid.UUID | None = None
    platform: str | None = None
    sentiment: Sentiment | None = None
    status: CommentStatus | None = None
    search: str | None = None
    page: int = 1
    per_page: int = 20


class ReplyRequest(BaseModel):
    message: str
    use_ai_draft: bool = False


class CommentStatusUpdate(BaseModel):
    status: CommentStatus


class CommentResponse(BaseModel):
    id: uuid.UUID
    platform_account_id: uuid.UUID
    content_id: uuid.UUID | None = None
    platform_comment_id: str
    parent_comment_id: uuid.UUID | None = None
    author_name: str
    author_profile_url: str | None = None
    message: str
    sentiment: Sentiment | None = None
    sentiment_score: float | None = None
    status: CommentStatus
    ai_reply_draft: str | None = None
    replied_at: datetime | None = None
    replied_by: uuid.UUID | None = None
    commented_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class SentimentStats(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    crisis: int = 0
    total: int = 0


class FilterRuleCreate(BaseModel):
    client_id: uuid.UUID
    rule_type: RuleType
    value: str = Field(max_length=500)
    action: FilterAction
    is_active: bool = True


class FilterRuleUpdate(BaseModel):
    rule_type: RuleType | None = None
    value: str | None = Field(None, max_length=500)
    action: FilterAction | None = None
    is_active: bool | None = None


class FilterRuleResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    rule_type: RuleType
    value: str
    action: FilterAction
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
