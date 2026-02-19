"""AI Tools API endpoints — copy generation, sentiment, RAG replies, chat."""
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.ai_tools import (
    ChatRequest,
    ChatResponse,
    ContentAnalyzeRequest,
    CopyDraft,
    CopyGenerateRequest,
    ReplyDraftRequest,
    SentimentBatchRequest,
    SentimentRequest,
    SentimentResult,
)
from app.schemas.common import APIResponse
from app.services.ai_service import ai_service

router = APIRouter()


# ── Copy Generation ──


@router.post("/generate-copy", response_model=APIResponse)
async def generate_copy(
    body: CopyGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate marketing copy drafts using LLM with brand guidelines."""
    drafts = await ai_service.generate_copy(
        db=db,
        client_id=body.client_id,
        prompt=body.prompt,
        content_type=body.content_type,
        platform=body.platform,
        num_drafts=body.num_drafts,
    )
    return {"status": "success", "data": drafts}


# ── Content Analysis ──


@router.post("/analyze/{content_id}", response_model=APIResponse)
async def analyze_content(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze content quality and get AI suggestions."""
    result = await ai_service.analyze_content(db, content_id)
    return {"status": "success", "data": result}


# ── Sentiment Analysis ──


@router.post("/sentiment", response_model=APIResponse)
async def analyze_sentiment(
    body: SentimentRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyze sentiment of a single text."""
    result = ai_service.analyze_sentiment(body.text)
    return {"status": "success", "data": result}


@router.post("/sentiment/batch", response_model=APIResponse)
async def analyze_sentiment_batch(
    body: SentimentBatchRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyze sentiment of multiple texts."""
    results = ai_service.analyze_sentiment_batch(body.texts)
    return {"status": "success", "data": results}


# ── RAG Reply Draft ──


@router.post("/suggest-reply/{comment_id}", response_model=APIResponse)
async def suggest_reply(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a reply draft for a comment using RAG pipeline."""
    reply = await ai_service.generate_reply_draft(db, comment_id)
    return {"status": "success", "data": {"reply": reply, "comment_id": comment_id}}


# ── AI Chat ──


@router.post("/chat", response_model=APIResponse)
async def ai_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """AI chatbot — non-streaming response."""
    if body.stream:
        # Return SSE streaming response
        async def event_generator():
            conversation_id = str(uuid.uuid4())
            async for chunk in ai_service.chat_stream(body.message, body.context):
                yield f"data: {chunk}\n\n"
            yield f"data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    reply = await ai_service.chat(body.message, body.context)
    return {
        "status": "success",
        "data": {"reply": reply, "conversation_id": str(uuid.uuid4())},
    }
