"""Content ORM model."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, pg_enum


class ContentType(str, enum.Enum):
    FEED = "feed"
    REEL = "reel"
    STORY = "story"
    SHORT = "short"
    CARD_NEWS = "card_news"


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    CLIENT_REVIEW = "client_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"


class Content(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "contents"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[ContentType] = mapped_column(pg_enum(ContentType, name="content_type"), nullable=False)
    status: Mapped[ContentStatus] = mapped_column(
        pg_enum(ContentStatus, name="content_status"), nullable=False, default=ContentStatus.DRAFT
    )
    media_urls: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    hashtags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    target_platforms: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    ai_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    client = relationship("Client", back_populates="contents")
    creator = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver = relationship("User", foreign_keys=[approved_by], lazy="selectin")
    approvals = relationship("ContentApproval", back_populates="content", lazy="noload")
    publishing_logs = relationship("PublishingLog", back_populates="content", lazy="noload")
    comments = relationship("CommentInbox", back_populates="content", lazy="noload")
