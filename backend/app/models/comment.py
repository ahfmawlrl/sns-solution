"""Comment inbox ORM model."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, pg_enum


class Sentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    CRISIS = "crisis"


class CommentStatus(str, enum.Enum):
    PENDING = "pending"
    REPLIED = "replied"
    HIDDEN = "hidden"
    FLAGGED = "flagged"


class CommentInbox(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "comments_inbox"

    platform_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False
    )
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contents.id"), nullable=True
    )
    platform_comment_id: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments_inbox.id"), nullable=True
    )
    author_name: Mapped[str] = mapped_column(String(200), nullable=False)
    author_profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[Sentiment | None] = mapped_column(pg_enum(Sentiment, name="sentiment"), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[CommentStatus] = mapped_column(
        pg_enum(CommentStatus, name="comment_status"), nullable=False, default=CommentStatus.PENDING
    )
    ai_reply_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    commented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    platform_account = relationship("PlatformAccount", back_populates="comments")
    content = relationship("Content", back_populates="comments")
    parent = relationship("CommentInbox", remote_side="CommentInbox.id", lazy="selectin")
    replier = relationship("User", lazy="selectin")
