"""AI tasks — HIGH queue.

Handles sentiment analysis, copy generation, RAG reply drafts, and metadata generation.
"""
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.ai_tasks.analyze_sentiment")
def analyze_sentiment(comment_id: str):
    """Analyze sentiment of a comment using KcELECTRA.

    Updates comments_inbox.sentiment and sentiment_score.
    If crisis detected, triggers crisis_alert notification.
    """
    from sqlalchemy import select, update
    from app.database import async_session_factory
    from app.models.comment import CommentInbox, Sentiment
    import asyncio

    async def _analyze():
        async with async_session_factory() as db:
            comment = (await db.execute(
                select(CommentInbox).where(CommentInbox.id == comment_id)
            )).scalar_one_or_none()

            if not comment:
                logger.warning("Comment %s not found for sentiment analysis", comment_id)
                return

            # Placeholder: actual ML model integration in STEP 20
            # For now, default to neutral
            sentiment = Sentiment.NEUTRAL
            score = 0.5

            await db.execute(
                update(CommentInbox)
                .where(CommentInbox.id == comment_id)
                .values(sentiment=sentiment, sentiment_score=score)
            )
            await db.commit()
            logger.info("Sentiment for comment %s: %s (%.2f)", comment_id, sentiment.value, score)

            # If crisis detected (very negative sentiment), push alert via Redis Pub/Sub
            if sentiment == Sentiment.NEGATIVE and score < 0.2:
                try:
                    import redis as sync_redis
                    from app.config import settings
                    import json
                    r = sync_redis.from_url(settings.REDIS_URL)
                    # Notify the content creator / account owner
                    # Use the platform_account's client to find relevant users
                    alert_data = {
                        "type": "crisis_alert",
                        "data": {
                            "comment_id": str(comment_id),
                            "platform": comment.platform.value if comment.platform else "unknown",
                            "message": comment.message[:200] if comment.message else "",
                            "sentiment_score": score,
                            "severity": "critical" if score < 0.1 else "warning",
                        }
                    }
                    # Publish to a general crisis channel for all connected managers
                    r.publish("ws:broadcast:crisis", json.dumps(alert_data))
                    # Also publish to specific user if platform_account has owner info
                    if comment.platform_account_id:
                        from app.models.platform_account import PlatformAccount
                        account = (await db.execute(
                            select(PlatformAccount).where(
                                PlatformAccount.id == comment.platform_account_id
                            )
                        )).scalar_one_or_none()
                        if account and account.client_id:
                            # Publish to client-specific channel
                            r.publish(
                                f"ws:user:client:{str(account.client_id)}",
                                json.dumps(alert_data),
                            )
                    r.close()
                except Exception:
                    logger.warning("Failed to push crisis alert WS notification")

    try:
        asyncio.get_event_loop().run_until_complete(_analyze())
    except RuntimeError:
        asyncio.run(_analyze())


@celery_app.task(name="app.tasks.ai_tasks.generate_copy")
def generate_copy(request_data: dict) -> dict:
    """Generate marketing copy using LLM.

    Args:
        request_data: {prompt, content_type, platform, client_id, brand_guidelines}

    Returns:
        dict with generated drafts
    """
    # Placeholder: actual LLM integration in STEP 19
    logger.info("Generating copy for: %s", request_data.get("content_type"))
    return {
        "drafts": [
            {"text": f"Draft 1 for {request_data.get('content_type', 'post')}", "tone": "friendly"},
            {"text": f"Draft 2 for {request_data.get('content_type', 'post')}", "tone": "professional"},
            {"text": f"Draft 3 for {request_data.get('content_type', 'post')}", "tone": "casual"},
        ]
    }


@celery_app.task(name="app.tasks.ai_tasks.generate_reply_draft")
def generate_reply_draft(comment_id: str, client_id: str):
    """Generate RAG-based reply draft for a comment.

    Uses FAQ/guidelines vector search + LLM to draft a reply.
    Updates comments_inbox.ai_reply_draft.
    """
    from sqlalchemy import select, update
    from app.database import async_session_factory
    from app.models.comment import CommentInbox
    import asyncio

    async def _generate():
        async with async_session_factory() as db:
            comment = (await db.execute(
                select(CommentInbox).where(CommentInbox.id == comment_id)
            )).scalar_one_or_none()

            if not comment:
                logger.warning("Comment %s not found for reply draft", comment_id)
                return

            # Placeholder: actual RAG pipeline in STEP 21
            draft = f"Thank you for your comment. We appreciate your feedback regarding: {comment.message[:50]}..."

            await db.execute(
                update(CommentInbox)
                .where(CommentInbox.id == comment_id)
                .values(ai_reply_draft=draft)
            )
            await db.commit()
            logger.info("Reply draft generated for comment %s", comment_id)

    try:
        asyncio.get_event_loop().run_until_complete(_generate())
    except RuntimeError:
        asyncio.run(_generate())


@celery_app.task(name="app.tasks.ai_tasks.generate_metadata")
def generate_metadata(content_id: str):
    """Generate AI metadata (hashtags, caption, alt text) for content.

    Updates contents.ai_metadata.
    """
    from sqlalchemy import select, update
    from app.database import async_session_factory
    from app.models.content import Content
    import asyncio

    async def _generate():
        async with async_session_factory() as db:
            content = (await db.execute(
                select(Content).where(Content.id == content_id)
            )).scalar_one_or_none()

            if not content:
                logger.warning("Content %s not found for metadata generation", content_id)
                return

            # Placeholder: actual LLM/VLM integration in STEP 19
            metadata = {
                "suggested_hashtags": ["#marketing", "#socialmedia", "#content"],
                "suggested_caption": f"Check out: {content.title}",
                "alt_text": "Image description placeholder",
            }

            await db.execute(
                update(Content)
                .where(Content.id == content_id)
                .values(ai_metadata=metadata)
            )
            await db.commit()
            logger.info("Metadata generated for content %s", content_id)

    try:
        asyncio.get_event_loop().run_until_complete(_generate())
    except RuntimeError:
        asyncio.run(_generate())
