"""Client ORM model."""
import enum
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, pg_enum


class ClientStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Client(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    brand_guidelines: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    manager_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[ClientStatus] = mapped_column(
        pg_enum(ClientStatus, name="client_status"), nullable=False, default=ClientStatus.ACTIVE
    )
    contract_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    manager = relationship("User", back_populates="managed_clients", lazy="selectin")
    platform_accounts = relationship("PlatformAccount", back_populates="client", lazy="selectin")
    user_assignments = relationship("UserClientAssignment", back_populates="client", lazy="selectin")
    contents = relationship("Content", back_populates="client", lazy="noload")
    faq_guidelines = relationship("FaqGuideline", back_populates="client", lazy="noload")
    filter_rules = relationship("FilterRule", back_populates="client", lazy="noload")
