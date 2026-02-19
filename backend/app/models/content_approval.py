"""Content approval ORM model."""
import uuid

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, pg_enum
from app.models.content import ContentStatus


class ContentApproval(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "content_approvals"

    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contents.id"), nullable=False)
    from_status: Mapped[ContentStatus] = mapped_column(pg_enum(ContentStatus, name="content_status", create_type=False), nullable=False)
    to_status: Mapped[ContentStatus] = mapped_column(pg_enum(ContentStatus, name="content_status", create_type=False), nullable=False)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    content = relationship("Content", back_populates="approvals")
    reviewer = relationship("User", lazy="selectin")
