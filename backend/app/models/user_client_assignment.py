"""User-Client assignment model."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, pg_enum


class RoleInClient(str, enum.Enum):
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class UserClientAssignment(Base, UUIDMixin):
    __tablename__ = "user_client_assignments"
    __table_args__ = (UniqueConstraint("user_id", "client_id", name="uq_user_client"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    role_in_client: Mapped[RoleInClient] = mapped_column(
        pg_enum(RoleInClient, name="role_in_client"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="client_assignments")
    client = relationship("Client", back_populates="user_assignments")
