"""AI service — orchestrates LLM, sentiment, RAG, and chat operations."""
import json
import logging
import re
import uuid as _uuid
from typing import Any
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.ai.llm_client import LLMClient
from app.integrations.ai.sentiment import sentiment_analyzer
from app.integrations.ai.rag import RAGPipeline
from app.models.client import Client
from app.models.content import Content
from app.models.comment import CommentInbox

logger = logging.getLogger(__name__)

# Keywords that indicate a data query
_DATA_QUERY_KEYWORDS = re.compile(
    r"데이터|통계|성과|게시물|콘텐츠|조회수|팔로워|몇\s*개|얼마나|best|worst|top|"
    r"평균|합계|총|증가|감소|비교|추이|리포트|보고서|engagement|reach|impression",
    re.IGNORECASE,
)

_DATA_AWARE_SYSTEM_PROMPT = """당신은 SNS 운영 관리 솔루션의 AI 어시스턴트입니다.
사용자의 데이터 분석 질문에 답변하고, SNS 운영 관련 조언을 제공합니다.

데이터베이스 테이블 정보:
- contents: id, client_id, title, body, content_type, status, target_platforms, published_at, created_at
- analytics_snapshots: id, platform_account_id, date, followers, reach, impressions, engagement_rate, likes, comments_count, shares, video_views
- comment_inbox: id, platform_account_id, author_name, message, sentiment, status, commented_at
- platform_accounts: id, client_id, platform (instagram/facebook/youtube), account_name

데이터 질의가 들어오면:
1. 어떤 데이터를 조회해야 하는지 설명하세요
2. 참고할 SQL 쿼리를 제시하세요
3. 예상 결과를 설명하세요
{client_context}
간결하고 유용한 답변을 해주세요."""

_DEFAULT_SYSTEM_PROMPT = """당신은 SNS 운영 관리 솔루션의 AI 어시스턴트입니다.
사용자의 데이터 분석 질문에 답변하고, SNS 운영 관련 조언을 제공합니다.
{client_context}
간결하고 유용한 답변을 해주세요."""


class ConversationManager:
    """Manage conversation history in Redis with TTL."""

    HISTORY_TTL = 3600 * 24  # 24 hours
    MAX_MESSAGES = 20

    @staticmethod
    async def get_history(conversation_id: str) -> list[dict]:
        """Get conversation history from Redis."""
        try:
            from app.utils.redis_client import get_redis
            redis = await get_redis()
            data = await redis.get(f"chat:history:{conversation_id}")
            if data:
                return json.loads(data)
        except Exception:
            pass
        return []

    @staticmethod
    async def add_message(conversation_id: str, role: str, content: str):
        """Add a message to conversation history."""
        try:
            from app.utils.redis_client import get_redis
            redis = await get_redis()
            key = f"chat:history:{conversation_id}"
            history: list[dict] = []
            data = await redis.get(key)
            if data:
                history = json.loads(data)
            history.append({"role": role, "content": content})
            # Keep only last MAX_MESSAGES
            history = history[-ConversationManager.MAX_MESSAGES:]
            await redis.set(key, json.dumps(history, ensure_ascii=False), ex=ConversationManager.HISTORY_TTL)
        except Exception:
            pass


class AIService:
    def __init__(self):
        self.llm = LLMClient()
        self.rag = RAGPipeline(llm=self.llm)

    # ── Copy Generation (STEP 19) ──

    async def generate_copy(
        self,
        db: AsyncSession,
        client_id: str,
        prompt: str,
        content_type: str = "feed",
        platform: str = "instagram",
        num_drafts: int = 3,
    ) -> list[dict[str, str]]:
        """Generate marketing copy drafts with brand guidelines context."""
        # Load client brand guidelines
        client = (await db.execute(
            select(Client).where(Client.id == _uuid.UUID(client_id))
        )).scalar_one_or_none()

        guidelines = ""
        if client and client.brand_guidelines:
            guidelines = f"브랜드: {client.name}\n"
            for k, v in client.brand_guidelines.items():
                guidelines += f"- {k}: {v}\n"

        tones = ["친근하고 캐주얼한", "전문적이고 신뢰감 있는", "유머러스하고 트렌디한"]
        drafts = []

        for i in range(min(num_drafts, len(tones))):
            system_prompt = f"""당신은 SNS 콘텐츠 카피라이터입니다.
{guidelines}
플랫폼: {platform}
콘텐츠 타입: {content_type}
톤: {tones[i]}

규칙:
- 플랫폼에 맞는 길이와 형식을 지켜주세요.
- 해시태그를 3-5개 포함하세요.
- 이모지를 적절히 활용하세요.
"""
            text = await self.llm.generate(system_prompt, prompt, max_tokens=500)
            drafts.append({"text": text, "tone": tones[i]})

        return drafts

    # ── Sentiment Analysis (STEP 20) ──

    def analyze_sentiment(self, text: str) -> dict[str, Any]:
        """Analyze text sentiment."""
        label, score = sentiment_analyzer.analyze(text)
        return {"sentiment": label, "score": round(score, 3)}

    def analyze_sentiment_batch(self, texts: list[str]) -> list[dict[str, Any]]:
        """Analyze sentiment for multiple texts."""
        results = sentiment_analyzer.analyze_batch(texts)
        return [{"sentiment": label, "score": round(score, 3)} for label, score in results]

    # ── RAG Reply Draft (STEP 21) ──

    async def generate_reply_draft(
        self,
        db: AsyncSession,
        comment_id: str,
    ) -> str:
        """Generate a reply draft for a comment using RAG pipeline."""
        comment = (await db.execute(
            select(CommentInbox).where(CommentInbox.id == _uuid.UUID(comment_id))
        )).scalar_one_or_none()

        if not comment:
            raise ValueError(f"Comment {comment_id} not found")

        # Get the client from the platform account
        from app.models.platform_account import PlatformAccount
        account = (await db.execute(
            select(PlatformAccount).where(PlatformAccount.id == comment.platform_account_id)
        )).scalar_one_or_none()

        if not account:
            raise ValueError("Platform account not found")

        client = (await db.execute(
            select(Client).where(Client.id == account.client_id)
        )).scalar_one_or_none()

        tone = "친절하고 전문적인"
        client_name = "브랜드"
        if client:
            client_name = client.name
            if client.brand_guidelines and "tone" in client.brand_guidelines:
                tone = client.brand_guidelines["tone"]

        reply = await self.rag.generate_reply_draft(
            db=db,
            comment_text=comment.message,
            client_id=str(account.client_id),
            client_name=client_name,
            tone=tone,
        )
        return reply

    # ── Content Analysis (STEP 19) ──

    async def analyze_content(self, db: AsyncSession, content_id: str) -> dict[str, Any]:
        """Analyze content quality and generate suggestions."""
        content = (await db.execute(
            select(Content).where(Content.id == _uuid.UUID(content_id))
        )).scalar_one_or_none()

        if not content:
            raise ValueError(f"Content {content_id} not found")

        system_prompt = """당신은 SNS 콘텐츠 분석 전문가입니다.
다음 콘텐츠를 분석하고 개선 사항을 제안해주세요.

분석 항목:
1. 전체 품질 점수 (1-10)
2. 강점
3. 개선 제안
4. 추천 해시태그
5. 최적 게시 시간 제안"""

        analysis = await self.llm.generate(
            system_prompt,
            f"제목: {content.title}\n본문: {content.body or '(없음)'}\n타입: {content.content_type.value}\n플랫폼: {', '.join(content.target_platforms)}",
        )
        return {"content_id": str(content_id), "analysis": analysis}

    # ── AI Chat (STEP 22) ──

    def _build_chat_system_prompt(
        self, message: str, context: dict[str, Any] | None = None,
    ) -> str:
        """Build the appropriate system prompt based on message content."""
        client_context = ""
        if context and context.get("client_id"):
            client_context = f"\n현재 선택된 클라이언트 ID: {context['client_id']}"

        is_data_query = bool(_DATA_QUERY_KEYWORDS.search(message))
        template = _DATA_AWARE_SYSTEM_PROMPT if is_data_query else _DEFAULT_SYSTEM_PROMPT
        return template.format(client_context=client_context)

    @staticmethod
    def _format_history_for_prompt(history: list[dict]) -> str:
        """Format conversation history into a prompt section."""
        if not history:
            return ""
        lines = ["\n[이전 대화 내역]"]
        for msg in history:
            role_label = "사용자" if msg["role"] == "user" else "어시스턴트"
            lines.append(f"{role_label}: {msg['content']}")
        lines.append("[대화 내역 끝]\n")
        return "\n".join(lines)

    async def chat(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        conversation_id: str | None = None,
    ) -> str:
        """Non-streaming chat response with data-aware context and conversation history."""
        system_prompt = self._build_chat_system_prompt(message, context)

        # Load conversation history
        history: list[dict] = []
        if conversation_id:
            history = await ConversationManager.get_history(conversation_id)
            history_text = self._format_history_for_prompt(history)
            if history_text:
                system_prompt += history_text

        # Save user message
        if conversation_id:
            await ConversationManager.add_message(conversation_id, "user", message)

        reply = await self.llm.generate(system_prompt, message)

        # Save assistant reply
        if conversation_id:
            await ConversationManager.add_message(conversation_id, "assistant", reply)

        return reply

    async def chat_stream(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        conversation_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Streaming chat response for SSE with data-aware context and conversation history."""
        system_prompt = self._build_chat_system_prompt(message, context)

        # Load conversation history
        if conversation_id:
            history = await ConversationManager.get_history(conversation_id)
            history_text = self._format_history_for_prompt(history)
            if history_text:
                system_prompt += history_text
            await ConversationManager.add_message(conversation_id, "user", message)

        collected_reply = []
        async for chunk in self.llm.stream(system_prompt, message):
            collected_reply.append(chunk)
            yield chunk

        # Save the full assistant reply
        if conversation_id:
            await ConversationManager.add_message(
                conversation_id, "assistant", "".join(collected_reply)
            )


ai_service = AIService()
