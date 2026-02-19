"""Tests for AI features — LLM, sentiment, RAG, embeddings, chat API."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.integrations.ai.sentiment import (
    SentimentAnalyzer,
    POSITIVE, NEGATIVE, NEUTRAL, CRISIS,
)
from app.integrations.ai.embeddings import chunk_text, EmbeddingService
from app.integrations.ai.llm_client import LLMClient
from app.models.client import Client
from app.models.content import Content, ContentType, ContentStatus
from app.models.comment import CommentInbox, CommentStatus
from app.models.platform_account import PlatformAccount, Platform
from app.models.faq_guideline import FaqGuideline, FaqCategory
from app.models.user import UserRole

from tests.conftest import _create_test_user


# ═══════════════════════════════════════════════════════
# Sentiment Analysis Tests
# ═══════════════════════════════════════════════════════


class TestSentimentAnalyzer:
    def setup_method(self):
        self.analyzer = SentimentAnalyzer(use_model=False)

    def test_positive_korean(self):
        label, score = self.analyzer.analyze("정말 좋아요! 최고입니다 감사합니다")
        assert label == POSITIVE
        assert score > 0.5

    def test_positive_english(self):
        label, score = self.analyzer.analyze("This is awesome! Great work, love it!")
        assert label == POSITIVE

    def test_negative_korean(self):
        label, score = self.analyzer.analyze("별로입니다 실망이에요 최악")
        assert label == NEGATIVE

    def test_negative_english(self):
        label, score = self.analyzer.analyze("This is terrible and disappointing")
        assert label == NEGATIVE

    def test_crisis_korean(self):
        label, score = self.analyzer.analyze("사기 아닌가요? 환불 해주세요 고소합니다")
        assert label == CRISIS
        assert score > 0.6

    def test_crisis_english(self):
        label, score = self.analyzer.analyze("This is fraud! I want a refund, scam!")
        assert label == CRISIS

    def test_neutral(self):
        label, score = self.analyzer.analyze("오늘 날씨가 좋네요")
        assert label == NEUTRAL

    def test_batch(self):
        texts = ["좋아요!", "최악 별로", "보통이네"]
        results = self.analyzer.analyze_batch(texts)
        assert len(results) == 3
        assert results[0][0] == POSITIVE
        assert results[1][0] == NEGATIVE
        assert results[2][0] == NEUTRAL


# ═══════════════════════════════════════════════════════
# Embedding / Chunk Tests
# ═══════════════════════════════════════════════════════


class TestEmbeddings:
    def test_chunk_short_text(self):
        chunks = chunk_text("Hello world", chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_chunk_long_text(self):
        text = "A" * 1200
        chunks = chunk_text(text, chunk_size=500, overlap=100)
        assert len(chunks) >= 3
        # First chunk
        assert len(chunks[0]) == 500
        # Overlap check: last 100 chars of chunk[0] == first 100 chars of chunk[1]
        assert chunks[0][-100:] == chunks[1][:100]

    def test_chunk_exact_size(self):
        text = "A" * 500
        chunks = chunk_text(text, chunk_size=500)
        assert len(chunks) == 1

    async def test_mock_embed_returns_correct_dimension(self):
        service = EmbeddingService()
        vector = service._mock_embed("test text")
        assert len(vector) == 1536

    async def test_mock_embed_deterministic(self):
        service = EmbeddingService()
        v1 = service._mock_embed("hello")
        v2 = service._mock_embed("hello")
        assert v1 == v2

    async def test_mock_embed_different_for_different_text(self):
        service = EmbeddingService()
        v1 = service._mock_embed("hello")
        v2 = service._mock_embed("world")
        assert v1 != v2


# ═══════════════════════════════════════════════════════
# LLM Client Tests (mock mode — no API key)
# ═══════════════════════════════════════════════════════


class TestLLMClient:
    async def test_mock_generate(self):
        client = LLMClient(provider="claude")
        result = await client.generate("system", "test prompt")
        assert "[Mock claude response]" in result
        assert "test prompt" in result

    async def test_mock_stream(self):
        client = LLMClient(provider="claude")
        chunks = []
        async for chunk in client.stream("system", "test prompt"):
            chunks.append(chunk)
        assert len(chunks) > 0
        full = "".join(chunks)
        assert "Mock" in full

    def test_unsupported_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            LLMClient(provider="nonexistent")


# ═══════════════════════════════════════════════════════
# AI API Endpoint Tests
# ═══════════════════════════════════════════════════════


async def _setup_client_with_comment(db_session):
    """Helper: create user, client, account, comment."""
    user, token = await _create_test_user(db_session, UserRole.OPERATOR)
    headers = {"Authorization": f"Bearer {token}"}

    client_obj = Client(
        id=uuid.uuid4(), name="Test Brand", status="active", manager_id=user.id,
        brand_guidelines={"tone": "친절한", "style": "모던"},
    )
    db_session.add(client_obj)
    await db_session.commit()

    account = PlatformAccount(
        id=uuid.uuid4(), client_id=client_obj.id,
        platform=Platform.INSTAGRAM, account_name="test_ig", access_token="tok",
    )
    db_session.add(account)
    await db_session.commit()

    content = Content(
        id=uuid.uuid4(), client_id=client_obj.id, title="Test Post",
        content_type=ContentType.FEED, status=ContentStatus.DRAFT,
        target_platforms=["instagram"], created_by=user.id, body="Great content here",
    )
    db_session.add(content)

    comment = CommentInbox(
        id=uuid.uuid4(), platform_account_id=account.id,
        platform_comment_id="pc_1", author_name="User1",
        message="이 제품 정말 좋아요! 추천합니다", status=CommentStatus.PENDING,
        commented_at=datetime.now(timezone.utc),
    )
    db_session.add(comment)

    faq = FaqGuideline(
        id=uuid.uuid4(), client_id=client_obj.id,
        category=FaqCategory.FAQ, title="감사 인사 응대",
        content="긍정적 댓글에는 감사 인사와 함께 추가 정보를 안내합니다.",
        is_active=True, priority=10,
    )
    db_session.add(faq)
    await db_session.commit()

    return user, headers, client_obj, content, comment


async def test_sentiment_api(client, db_session):
    user, headers, *_ = await _setup_client_with_comment(db_session)

    resp = await client.post(
        "/api/v1/ai/sentiment",
        json={"text": "정말 좋아요! 최고입니다"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["sentiment"] == "positive"
    assert data["score"] > 0.5


async def test_sentiment_batch_api(client, db_session):
    user, headers, *_ = await _setup_client_with_comment(db_session)

    resp = await client.post(
        "/api/v1/ai/sentiment/batch",
        json={"texts": ["좋아요!", "최악이에요", "보통"]},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 3


async def test_generate_copy_api(client, db_session):
    user, headers, client_obj, *_ = await _setup_client_with_comment(db_session)

    resp = await client.post(
        "/api/v1/ai/generate-copy",
        json={
            "client_id": str(client_obj.id),
            "prompt": "새해 맞이 할인 이벤트 홍보 게시물",
            "content_type": "feed",
            "platform": "instagram",
            "num_drafts": 2,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    assert "text" in data[0]
    assert "tone" in data[0]


async def test_analyze_content_api(client, db_session):
    user, headers, _, content, _ = await _setup_client_with_comment(db_session)

    resp = await client.post(
        f"/api/v1/ai/analyze/{content.id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["content_id"] == str(content.id)
    assert "analysis" in data


async def test_suggest_reply_api(client, db_session):
    user, headers, _, _, comment = await _setup_client_with_comment(db_session)

    resp = await client.post(
        f"/api/v1/ai/suggest-reply/{comment.id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "reply" in data
    assert data["comment_id"] == str(comment.id)


async def test_chat_api(client, db_session):
    user, headers, *_ = await _setup_client_with_comment(db_session)

    resp = await client.post(
        "/api/v1/ai/chat",
        json={"message": "지난주 인스타 베스트 게시물은?", "context": {}},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "reply" in data
    assert "conversation_id" in data


async def test_chat_unauthenticated(client):
    resp = await client.post(
        "/api/v1/ai/chat",
        json={"message": "hello"},
    )
    assert resp.status_code in (401, 403)


async def test_analyze_content_not_found(client, db_session):
    user, headers, *_ = await _setup_client_with_comment(db_session)

    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/ai/analyze/{fake_id}",
        headers=headers,
    )
    assert resp.status_code in (400, 404, 500)
