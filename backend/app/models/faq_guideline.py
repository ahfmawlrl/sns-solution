"""FAQ/Guideline ORM model."""
import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, pg_enum


class FaqCategory(str, enum.Enum):
    FAQ = "faq"
    TONE_MANNER = "tone_manner"
    CRISIS_SCENARIO = "crisis_scenario"
    TEMPLATE = "template"


class FaqGuideline(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "faq_guidelines"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    category: Mapped[FaqCategory] = mapped_column(pg_enum(FaqCategory, name="faq_category"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    client = relationship("Client", back_populates="faq_guidelines")
