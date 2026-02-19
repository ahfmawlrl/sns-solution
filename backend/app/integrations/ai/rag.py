"""RAG (Retrieval-Augmented Generation) pipeline for comment reply drafts.

Uses FAQ/guideline vector search via pgvector + LLM to generate contextual replies.
"""
import logging
import uuid as _uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.ai.llm_client import LLMClient
from app.integrations.ai.embeddings import EmbeddingService, chunk_text
from app.models.vector_embedding import VectorEmbedding
from app.models.faq_guideline import FaqGuideline

logger = logging.getLogger(__name__)

REPLY_SYSTEM_PROMPT_TEMPLATE = """당신은 {client_name}의 SNS 운영 담당자입니다.
다음 가이드라인을 참고하여 댓글에 대한 응대 초안을 작성하세요.

[가이드라인]
{context}

[톤앤매너]
{tone}

규칙:
- 브랜드 가이드라인을 준수하세요.
- 친절하고 전문적인 톤을 유지하세요.
- 답변은 간결하게 작성하세요 (1-3문장).
- 필요한 경우 고객센터 안내를 포함하세요.
"""


class RAGPipeline:
    """FAQ/guideline-based reply draft generation using RAG."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        embedder: EmbeddingService | None = None,
    ):
        self.llm = llm or LLMClient()
        self.embedder = embedder or EmbeddingService()

    async def generate_reply_draft(
        self,
        db: AsyncSession,
        comment_text: str,
        client_id: str,
        client_name: str = "브랜드",
        tone: str = "친절하고 전문적인",
        top_k: int = 5,
    ) -> str:
        """Generate a reply draft for a comment using RAG.

        Steps:
            1. Embed the comment text
            2. Search for similar FAQ/guidelines (by client_id)
            3. Build context from retrieved documents
            4. Generate reply with LLM

        Args:
            db: Database session
            comment_text: The comment to reply to
            client_id: Client UUID for scoping FAQ search
            client_name: Client name for prompt
            tone: Brand tone description
            top_k: Number of similar documents to retrieve

        Returns:
            Generated reply draft text
        """
        # Step 1 & 2: Retrieve relevant FAQ context
        context = await self._retrieve_context(db, comment_text, client_id, top_k)

        if not context:
            # Fallback: try to get any FAQ for this client
            context = await self._get_fallback_context(db, client_id)

        # Step 3: Build prompt
        system_prompt = REPLY_SYSTEM_PROMPT_TEMPLATE.format(
            client_name=client_name,
            context=context or "가이드라인이 등록되지 않았습니다. 일반적인 응대를 해주세요.",
            tone=tone,
        )

        # Step 4: Generate with LLM
        reply = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=f"다음 댓글에 대한 응대 초안을 작성해주세요:\n\n{comment_text}",
            max_tokens=500,
            temperature=0.7,
        )

        logger.info("Generated reply draft for client %s (context docs: %s)", client_id, "found" if context else "none")
        return reply

    async def _retrieve_context(
        self, db: AsyncSession, query_text: str, client_id: str, top_k: int
    ) -> str:
        """Retrieve similar FAQ/guideline chunks from vector store using cosine similarity."""
        # Step 1: Generate query embedding
        query_embedding = await self.embedder.embed(query_text)

        # Step 2: Try pgvector cosine similarity search
        try:
            result = await db.execute(
                text(
                    "SELECT chunk_text, 1 - (embedding <=> :query_vec) AS similarity "
                    "FROM vector_embeddings "
                    "WHERE source_type = 'faq_guideline' "
                    "AND metadata_->>'client_id' = :client_id "
                    "ORDER BY embedding <=> :query_vec "
                    "LIMIT :top_k"
                ),
                {
                    "query_vec": str(query_embedding),
                    "client_id": client_id,
                    "top_k": top_k,
                },
            )
            rows = result.fetchall()
            if rows:
                chunks = [row[0] for row in rows]
                return "\n---\n".join(chunks)
        except Exception:
            logger.debug("pgvector similarity search unavailable, using fallback")

        # Fallback: simple metadata filtering without vector similarity
        result = await db.execute(
            select(VectorEmbedding).where(
                VectorEmbedding.source_type == "faq_guideline",
                VectorEmbedding.metadata_["client_id"].astext == client_id,
            ).limit(top_k)
        )
        embeddings = result.scalars().all()
        if not embeddings:
            return ""
        chunks = [e.chunk_text for e in embeddings]
        return "\n---\n".join(chunks)

    async def _get_fallback_context(self, db: AsyncSession, client_id: str) -> str:
        """Get FAQ content directly when no embeddings exist."""
        result = await db.execute(
            select(FaqGuideline).where(
                FaqGuideline.client_id == _uuid.UUID(client_id),
                FaqGuideline.is_active.is_(True),
            ).order_by(FaqGuideline.priority.desc()).limit(5)
        )
        faqs = result.scalars().all()
        if not faqs:
            return ""
        return "\n---\n".join(f"[{f.category.value}] {f.title}\n{f.content}" for f in faqs)

    async def index_faq(
        self,
        db: AsyncSession,
        faq: FaqGuideline,
    ):
        """Index a FAQ/guideline into the vector store.

        Chunks the text, generates embeddings, and stores in vector_embeddings.
        """
        full_text = f"{faq.title}\n{faq.content}"
        chunks = chunk_text(full_text, chunk_size=500, overlap=100)

        # Delete existing embeddings for this source
        await db.execute(
            select(VectorEmbedding).where(
                VectorEmbedding.source_type == "faq_guideline",
                VectorEmbedding.source_id == faq.id,
            )
        )

        for i, chunk in enumerate(chunks):
            embedding_vector = await self.embedder.embed(chunk)
            ve = VectorEmbedding(
                source_type="faq_guideline",
                source_id=faq.id,
                chunk_index=i,
                chunk_text=chunk,
                metadata_={"client_id": str(faq.client_id)},
            )
            db.add(ve)

        await db.flush()
        logger.info("Indexed FAQ %s: %d chunks", faq.id, len(chunks))
