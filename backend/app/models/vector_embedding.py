"""Vector embedding ORM model (pgvector)."""
import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# Note: pgvector column type will be used via raw SQL or pgvector extension
# For now, store as a placeholder; actual vector ops use pgvector


class VectorEmbedding(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vector_embeddings"

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    # embedding column will be added via Alembic migration with vector(1536) type
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
