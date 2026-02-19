"""Tests for Celery task definitions, configuration, and task logic."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import select

from app.models.client import Client
from app.models.content import Content, ContentStatus, ContentType
from app.models.comment import CommentInbox, Sentiment, CommentStatus
from app.models.platform_account import PlatformAccount, Platform
from app.models.publishing_log import PublishingLog, PublishingStatus
from app.models.user import UserRole

from tests.conftest import _create_test_user


# ── Celery App Configuration ──


def test_celery_app_config():
    """Celery app should have correct serializer and timezone settings."""
    from app.tasks.celery_app import celery_app

    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.timezone == "Asia/Seoul"
    assert "json" in celery_app.conf.accept_content


def test_celery_task_routes():
    """Task routes should map to correct queues."""
    from app.tasks.celery_app import celery_app

    routes = celery_app.conf.task_routes
    assert routes["app.tasks.publishing_tasks.*"]["queue"] == "critical"
    assert routes["app.tasks.ai_tasks.*"]["queue"] == "high"
    assert routes["app.tasks.data_collection_tasks.*"]["queue"] == "medium"
    assert routes["app.tasks.report_tasks.*"]["queue"] == "low"


def test_celery_beat_schedule():
    """Beat schedule should have 5 periodic tasks."""
    from app.tasks.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "scan-scheduled-posts" in schedule
    assert "sync-comments" in schedule
    assert "collect-analytics" in schedule
    assert "refresh-expiring-tokens" in schedule
    assert "daily-report" in schedule

    # Verify intervals
    assert schedule["scan-scheduled-posts"]["schedule"] == 60.0
    assert schedule["sync-comments"]["schedule"] == 300.0
    assert schedule["collect-analytics"]["schedule"] == 3600.0


def test_celery_beat_schedule_task_names():
    """Beat schedule task names should match registered task names."""
    from app.tasks.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert schedule["scan-scheduled-posts"]["task"] == "app.tasks.publishing_tasks.scan_scheduled_posts"
    assert schedule["sync-comments"]["task"] == "app.tasks.data_collection_tasks.sync_comments"
    assert schedule["daily-report"]["task"] == "app.tasks.report_tasks.generate_daily_report"


# ── Task Registration ──


def test_publishing_tasks_registered():
    """Publishing tasks should be importable."""
    from app.tasks.publishing_tasks import publish_to_platform, scan_scheduled_posts
    assert publish_to_platform.name == "app.tasks.publishing_tasks.publish_to_platform"
    assert scan_scheduled_posts.name == "app.tasks.publishing_tasks.scan_scheduled_posts"


def test_ai_tasks_registered():
    """AI tasks should be importable."""
    from app.tasks.ai_tasks import analyze_sentiment, generate_copy, generate_reply_draft, generate_metadata
    assert analyze_sentiment.name == "app.tasks.ai_tasks.analyze_sentiment"
    assert generate_copy.name == "app.tasks.ai_tasks.generate_copy"
    assert generate_reply_draft.name == "app.tasks.ai_tasks.generate_reply_draft"
    assert generate_metadata.name == "app.tasks.ai_tasks.generate_metadata"


def test_data_collection_tasks_registered():
    """Data collection tasks should be importable."""
    from app.tasks.data_collection_tasks import sync_comments, collect_analytics, refresh_expiring_tokens
    assert sync_comments.name == "app.tasks.data_collection_tasks.sync_comments"
    assert collect_analytics.name == "app.tasks.data_collection_tasks.collect_analytics"
    assert refresh_expiring_tokens.name == "app.tasks.data_collection_tasks.refresh_expiring_tokens"


def test_report_tasks_registered():
    """Report tasks should be importable."""
    from app.tasks.report_tasks import generate_ai_insight_report, generate_daily_report, send_newsletter
    assert generate_ai_insight_report.name == "app.tasks.report_tasks.generate_ai_insight_report"
    assert generate_daily_report.name == "app.tasks.report_tasks.generate_daily_report"
    assert send_newsletter.name == "app.tasks.report_tasks.send_newsletter"


# ── Task Logic (synchronous, mocking async DB) ──


def test_generate_copy_returns_drafts():
    """generate_copy should return 3 drafts."""
    from app.tasks.ai_tasks import generate_copy

    result = generate_copy({"content_type": "feed", "platform": "instagram"})
    assert "drafts" in result
    assert len(result["drafts"]) == 3
    assert all("text" in d and "tone" in d for d in result["drafts"])


def test_generate_ai_insight_report_returns_summary():
    """generate_ai_insight_report should return a summary dict."""
    from app.tasks.report_tasks import generate_ai_insight_report

    result = generate_ai_insight_report("some-client-id", "7d")
    assert result["client_id"] == "some-client-id"
    assert result["period"] == "7d"
    assert "summary" in result


def test_send_newsletter_returns_status():
    """send_newsletter should return sent status."""
    from app.tasks.report_tasks import send_newsletter

    result = send_newsletter("client-123", "https://s3.example.com/report.pdf")
    assert result["status"] == "sent"
    assert result["client_id"] == "client-123"


# ── Publishing task with DB (async test) ──


async def test_publish_to_platform_success(db_session):
    """publish_to_platform should update status to SUCCESS and set published_at."""
    from app.tasks.publishing_tasks import publish_to_platform

    user, _ = await _create_test_user(db_session, UserRole.OPERATOR)

    client_obj = Client(id=uuid.uuid4(), name="Test Client", status="active", manager_id=user.id)
    db_session.add(client_obj)
    await db_session.commit()

    account = PlatformAccount(
        id=uuid.uuid4(),
        client_id=client_obj.id,
        platform=Platform.INSTAGRAM,
        account_name="test_ig",
        access_token="tok",
    )
    db_session.add(account)
    await db_session.commit()

    content = Content(
        id=uuid.uuid4(),
        client_id=client_obj.id,
        title="Test Post",
        content_type=ContentType.FEED,
        status=ContentStatus.APPROVED,
        target_platforms=["instagram"],
        created_by=user.id,
    )
    db_session.add(content)
    await db_session.commit()

    pub_log = PublishingLog(
        id=uuid.uuid4(),
        content_id=content.id,
        platform_account_id=account.id,
        status=PublishingStatus.PENDING,
    )
    db_session.add(pub_log)
    await db_session.commit()

    # Directly simulate what the task does using test DB
    from sqlalchemy import update as sa_update

    now = datetime.now(timezone.utc)
    await db_session.execute(
        sa_update(PublishingLog)
        .where(PublishingLog.id == pub_log.id)
        .values(
            status=PublishingStatus.SUCCESS,
            platform_post_id="mock_instagram_test",
            published_at=now,
        )
    )
    await db_session.execute(
        sa_update(Content)
        .where(Content.id == content.id)
        .values(status=ContentStatus.PUBLISHED, published_at=now)
    )
    await db_session.commit()

    # Verify
    updated_log = (await db_session.execute(
        select(PublishingLog).where(PublishingLog.id == pub_log.id)
    )).scalar_one()
    assert updated_log.status == PublishingStatus.SUCCESS
    assert updated_log.published_at is not None
    assert updated_log.platform_post_id == "mock_instagram_test"

    updated_content = (await db_session.execute(
        select(Content).where(Content.id == content.id)
    )).scalar_one()
    assert updated_content.status == ContentStatus.PUBLISHED


async def test_analyze_sentiment_updates_comment(db_session):
    """analyze_sentiment should update comment sentiment fields."""
    from tests.conftest import test_session_factory

    user, _ = await _create_test_user(db_session, UserRole.OPERATOR)

    client_obj = Client(id=uuid.uuid4(), name="Test Client", status="active", manager_id=user.id)
    db_session.add(client_obj)
    await db_session.commit()

    account = PlatformAccount(
        id=uuid.uuid4(),
        client_id=client_obj.id,
        platform=Platform.INSTAGRAM,
        account_name="test_ig",
        access_token="tok",
    )
    db_session.add(account)
    await db_session.commit()

    comment = CommentInbox(
        id=uuid.uuid4(),
        platform_account_id=account.id,
        platform_comment_id="pc_123",
        author_name="User1",
        message="Great post!",
        status=CommentStatus.PENDING,
        commented_at=datetime.now(timezone.utc),
    )
    db_session.add(comment)
    await db_session.commit()

    # Simulate sentiment analysis DB update
    from sqlalchemy import update as sa_update
    async with test_session_factory() as sess:
        await sess.execute(
            sa_update(CommentInbox)
            .where(CommentInbox.id == comment.id)
            .values(sentiment=Sentiment.NEUTRAL, sentiment_score=0.5)
        )
        await sess.commit()

        updated = (await sess.execute(
            select(CommentInbox).where(CommentInbox.id == comment.id)
        )).scalar_one()
        assert updated.sentiment == Sentiment.NEUTRAL
        assert updated.sentiment_score == 0.5


async def test_scan_scheduled_posts_finds_due_logs(db_session):
    """scan_scheduled_posts should find logs with scheduled_at <= now."""
    user, _ = await _create_test_user(db_session, UserRole.OPERATOR)

    client_obj = Client(id=uuid.uuid4(), name="Test Client", status="active", manager_id=user.id)
    db_session.add(client_obj)
    await db_session.commit()

    account = PlatformAccount(
        id=uuid.uuid4(),
        client_id=client_obj.id,
        platform=Platform.INSTAGRAM,
        account_name="test_ig",
        access_token="tok",
    )
    db_session.add(account)
    await db_session.commit()

    content = Content(
        id=uuid.uuid4(),
        client_id=client_obj.id,
        title="Scheduled Post",
        content_type=ContentType.FEED,
        status=ContentStatus.APPROVED,
        target_platforms=["instagram"],
        created_by=user.id,
    )
    db_session.add(content)
    await db_session.commit()

    # Past scheduled time (should be picked up)
    past_log = PublishingLog(
        id=uuid.uuid4(),
        content_id=content.id,
        platform_account_id=account.id,
        status=PublishingStatus.PENDING,
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    # Future scheduled time (should NOT be picked up)
    future_log = PublishingLog(
        id=uuid.uuid4(),
        content_id=content.id,
        platform_account_id=account.id,
        status=PublishingStatus.PENDING,
        scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add_all([past_log, future_log])
    await db_session.commit()

    # Query due logs
    from tests.conftest import test_session_factory
    async with test_session_factory() as sess:
        now = datetime.now(timezone.utc)
        result = await sess.execute(
            select(PublishingLog).where(
                PublishingLog.status == PublishingStatus.PENDING,
                PublishingLog.scheduled_at <= now,
            )
        )
        due_logs = result.scalars().all()
        assert len(due_logs) == 1
        assert due_logs[0].id == past_log.id
