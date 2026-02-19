"""Pydantic schemas for AI tools API."""
from pydantic import BaseModel, Field
from typing import Any


class CopyGenerateRequest(BaseModel):
    client_id: str
    prompt: str
    content_type: str = "feed"
    platform: str = "instagram"
    num_drafts: int = Field(default=3, ge=1, le=5)


class CopyDraft(BaseModel):
    text: str
    tone: str


class ContentAnalyzeRequest(BaseModel):
    content_id: str


class ReplyDraftRequest(BaseModel):
    comment_id: str


class SentimentRequest(BaseModel):
    text: str


class SentimentBatchRequest(BaseModel):
    texts: list[str] = Field(..., max_length=50)


class SentimentResult(BaseModel):
    sentiment: str
    score: float


class ChatRequest(BaseModel):
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str | None = None
