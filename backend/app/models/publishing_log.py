"""Publishing log ORM model."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, pg_enum


class PublishingStatus(str, enum.Enum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PublishingLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "publishing_logs"

    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contents.id"), nullable=False)
    platform_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False
    )
    status: Mapped[PublishingStatus] = mapped_column(pg_enum(PublishingStatus, name="publishing_status"), nullable=False)
    platform_post_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    platform_post_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationships
    content = relationship("Content", back_populates="publishing_logs")
    platform_account = relationship("PlatformAccount", back_populates="publishing_logs")
