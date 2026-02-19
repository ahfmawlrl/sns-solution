"""Tests for Publishing API (6 endpoints)."""
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.content import Content, ContentStatus, ContentType
from app.models.platform_account import Platform, PlatformAccount
from app.models.publishing_log import PublishingLog, PublishingStatus
from app.models.user import User, UserRole
from tests.conftest import _create_test_user


pytestmark = pytest.mark.anyio


async def _setup_publishing(db: AsyncSession, user: User):
    """Create client, platform account, and approved content."""
    client_obj = Client(name="Pub Client", industry="Media", manager_id=user.id)
    db.add(client_obj)
    await db.flush()

    account = PlatformAccount(
        client_id=client_obj.id,
        platform=Platform.INSTAGRAM,
        account_name="test_insta",
        access_token="tok",
    )
    db.add(account)
    await db.flush()

    content = Content(
        client_id=client_obj.id,
        title="Approved Post",
        content_type=ContentType.FEED,
        target_platforms=["instagram"],
        status=ContentStatus.APPROVED,
        created_by=user.id,
    )
    db.add(content)
    await db.commit()
    await db.refresh(client_obj)
    await db.refresh(account)
    await db.refresh(content)
    return client_obj, account, content


# --- POST /publishing/schedule ---

async def test_schedule_publish(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, account, content = await _setup_publishing(db_session, admin_user)
    payload = {
        "content_id": str(content.id),
        "platform_account_ids": [str(account.id)],
        "scheduled_at": "2026-04-01T10:00:00Z",
    }
    resp = await client.post("/api/v1/publishing/schedule", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["status"] == "pending"


async def test_schedule_non_approved_fails(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = Client(name="C", industry="T", manager_id=admin_user.id)
    db_session.add(c)
    await db_session.flush()
    account = PlatformAccount(
        client_id=c.id, platform=Platform.INSTAGRAM,
        account_name="a", access_token="t",
    )
    db_session.add(account)
    await db_session.flush()
    content = Content(
        client_id=c.id, title="Draft", content_type=ContentType.FEED,
        target_platforms=["instagram"], status=ContentStatus.DRAFT, created_by=admin_user.id,
    )
    db_session.add(content)
    await db_session.commit()
    payload = {
        "content_id": str(content.id),
        "platform_account_ids": [str(account.id)],
        "scheduled_at": "2026-04-01T10:00:00Z",
    }
    resp = await client.post("/api/v1/publishing/schedule", json=payload, headers=headers)
    assert resp.status_code == 400


# --- POST /publishing/now ---

async def test_publish_now(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, account, content = await _setup_publishing(db_session, admin_user)
    payload = {
        "content_id": str(content.id),
        "platform_account_ids": [str(account.id)],
    }
    resp = await client.post("/api/v1/publishing/now", json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["data"][0]["status"] == "publishing"


# --- GET /publishing/queue ---

async def test_get_queue(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, account, content = await _setup_publishing(db_session, admin_user)
    log = PublishingLog(
        content_id=content.id, platform_account_id=account.id,
        status=PublishingStatus.PENDING,
        scheduled_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )
    db_session.add(log)
    await db_session.commit()
    resp = await client.get("/api/v1/publishing/queue", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] >= 1


# --- DELETE /publishing/{id}/cancel ---

async def test_cancel_pending(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, account, content = await _setup_publishing(db_session, admin_user)
    log = PublishingLog(
        content_id=content.id, platform_account_id=account.id,
        status=PublishingStatus.PENDING,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    resp = await client.delete(f"/api/v1/publishing/{log.id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "cancelled"


async def test_cancel_non_pending_fails(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, account, content = await _setup_publishing(db_session, admin_user)
    log = PublishingLog(
        content_id=content.id, platform_account_id=account.id,
        status=PublishingStatus.SUCCESS,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    resp = await client.delete(f"/api/v1/publishing/{log.id}/cancel", headers=headers)
    assert resp.status_code == 400


# --- GET /publishing/history ---

async def test_get_history(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, account, content = await _setup_publishing(db_session, admin_user)
    log = PublishingLog(
        content_id=content.id, platform_account_id=account.id,
        status=PublishingStatus.SUCCESS,
    )
    db_session.add(log)
    await db_session.commit()
    resp = await client.get("/api/v1/publishing/history", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] >= 1


# --- POST /publishing/{id}/retry ---

async def test_retry_failed(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, account, content = await _setup_publishing(db_session, admin_user)
    log = PublishingLog(
        content_id=content.id, platform_account_id=account.id,
        status=PublishingStatus.FAILED,
        error_message="API Error",
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    resp = await client.post(f"/api/v1/publishing/{log.id}/retry", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "publishing"
    assert data["retry_count"] == 1


async def test_retry_non_failed_fails(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, account, content = await _setup_publishing(db_session, admin_user)
    log = PublishingLog(
        content_id=content.id, platform_account_id=account.id,
        status=PublishingStatus.SUCCESS,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    resp = await client.post(f"/api/v1/publishing/{log.id}/retry", headers=headers)
    assert resp.status_code == 400
