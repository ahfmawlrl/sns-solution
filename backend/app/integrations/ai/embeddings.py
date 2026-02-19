"""Text embedding service for vector search (pgvector)."""
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks.

    Args:
        text: Full text to split
        chunk_size: Max characters per chunk
        overlap: Character overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


class EmbeddingService:
    """Generate text embeddings for pgvector storage.

    Uses OpenAI's text-embedding-3-small by default.
    Falls back to a simple hash-based mock when API key is unavailable.
    """

    def __init__(self, model: str | None = None):
        self.model = model or settings.EMBEDDING_MODEL
        self.dimension = 1536  # text-embedding-3-small

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text.

        Returns a list of floats (dimension = 1536 for text-embedding-3-small).
        """
        if settings.OPENAI_API_KEY:
            return await self._embed_openai(text)

        # Mock embedding for development/testing
        return self._mock_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if settings.OPENAI_API_KEY:
            return await self._embed_openai_batch(texts)
        return [self._mock_embed(t) for t in texts]

    async def _embed_openai(self, text: str) -> list[float]:
        import openai

        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            response = await client.embeddings.create(
                model=self.model,
                input=text[:8000],  # Token limit safety
            )
            return response.data[0].embedding
        finally:
            await client.close()

    async def _embed_openai_batch(self, texts: list[str]) -> list[list[float]]:
        import openai

        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            response = await client.embeddings.create(
                model=self.model,
                input=[t[:8000] for t in texts],
            )
            return [item.embedding for item in response.data]
        finally:
            await client.close()

    def _mock_embed(self, text: str) -> list[float]:
        """Simple deterministic mock embedding based on text hash."""
        import hashlib

        h = hashlib.sha256(text.encode()).hexdigest()
        # Generate a deterministic vector from hash
        vector = []
        for i in range(0, min(len(h), self.dimension * 2), 2):
            val = int(h[i % len(h)], 16) / 15.0 - 0.5  # normalize to [-0.5, 0.5]
            vector.append(val)
        # Pad to dimension
        while len(vector) < self.dimension:
            vector.append(0.0)
        return vector[:self.dimension]


embedding_service = EmbeddingService()
