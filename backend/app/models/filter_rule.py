"""Filter rule ORM model."""
import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, pg_enum


class RuleType(str, enum.Enum):
    KEYWORD = "keyword"
    PATTERN = "pattern"
    USER_BLOCK = "user_block"


class FilterAction(str, enum.Enum):
    HIDE = "hide"
    FLAG = "flag"
    DELETE = "delete"


class FilterRule(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "filter_rules"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(pg_enum(RuleType, name="rule_type"), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    action: Mapped[FilterAction] = mapped_column(pg_enum(FilterAction, name="filter_action"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    client = relationship("Client", back_populates="filter_rules")
