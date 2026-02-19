"""Tests for Notifications API (4 endpoints)."""
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPriority, NotificationType
from app.models.user import User, UserRole
from tests.conftest import _create_test_user


pytestmark = pytest.mark.anyio


async def _create_notification(db: AsyncSession, user: User, is_read: bool = False) -> Notification:
    notif = Notification(
        user_id=user.id,
        type=NotificationType.SYSTEM,
        title="Test Notification",
        message="This is a test notification",
        priority=NotificationPriority.NORMAL,
        is_read=is_read,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


# --- GET /notifications ---

async def test_list_notifications(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    await _create_notification(db_session, admin_user)
    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] >= 1


async def test_list_notifications_filter_unread(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    await _create_notification(db_session, admin_user, is_read=False)
    await _create_notification(db_session, admin_user, is_read=True)
    resp = await client.get("/api/v1/notifications?is_read=false", headers=headers)
    assert resp.status_code == 200
    for n in resp.json()["data"]:
        assert n["is_read"] is False


# --- GET /notifications/unread-count ---

async def test_unread_count(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    await _create_notification(db_session, admin_user, is_read=False)
    await _create_notification(db_session, admin_user, is_read=False)
    await _create_notification(db_session, admin_user, is_read=True)
    resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["count"] >= 2


# --- PATCH /notifications/{id}/read ---

async def test_mark_read(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    notif = await _create_notification(db_session, admin_user)
    resp = await client.patch(f"/api/v1/notifications/{notif.id}/read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_read"] is True
    assert resp.json()["data"]["read_at"] is not None


async def test_mark_read_not_found(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.patch(f"/api/v1/notifications/{uuid.uuid4()}/read", headers=headers)
    assert resp.status_code == 404


async def test_mark_read_other_user(client: AsyncClient, admin_auth, db_session: AsyncSession):
    """Cannot read another user's notification."""
    other_user, _ = await _create_test_user(db_session, UserRole.OPERATOR)
    notif = await _create_notification(db_session, other_user)
    _, headers = admin_auth
    resp = await client.patch(f"/api/v1/notifications/{notif.id}/read", headers=headers)
    assert resp.status_code == 404


# --- PATCH /notifications/read-all ---

async def test_mark_all_read(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    await _create_notification(db_session, admin_user, is_read=False)
    await _create_notification(db_session, admin_user, is_read=False)
    resp = await client.patch("/api/v1/notifications/read-all", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["updated_count"] >= 2

    # Verify unread count is 0
    resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert resp.json()["data"]["count"] == 0
