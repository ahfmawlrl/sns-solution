"""Platform account ORM model."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, pg_enum


class Platform(str, enum.Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"


class PlatformAccount(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "platform_accounts"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    platform: Mapped[Platform] = mapped_column(pg_enum(Platform, name="platform"), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    client = relationship("Client", back_populates="platform_accounts")
    comments = relationship("CommentInbox", back_populates="platform_account", lazy="noload")
    analytics_snapshots = relationship("AnalyticsSnapshot", back_populates="platform_account", lazy="noload")
    publishing_logs = relationship("PublishingLog", back_populates="platform_account", lazy="noload")
