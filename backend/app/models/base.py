"""SQLAlchemy base model with UUID PK and timestamp mixins."""
import enum
import uuid
from datetime import datetime
from typing import Any, Type

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def pg_enum(enum_class: Type[enum.Enum], **kwargs: Any) -> Enum:
    """Create an SQLAlchemy Enum that stores enum VALUES (not names) in PostgreSQL.

    SQLAlchemy's default Enum uses Python enum *names* (e.g. 'ADMIN') as DB values.
    Our migrations store lowercase *values* (e.g. 'admin'), so we need this helper
    to set values_callable explicitly.
    """
    return Enum(
        enum_class,
        values_callable=lambda obj: [e.value for e in obj],
        **kwargs,
    )


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
