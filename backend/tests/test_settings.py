"""Tests for Settings API (7 endpoints)."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.platform_account import Platform, PlatformAccount
from app.models.user import User, UserRole
from tests.conftest import _create_test_user


pytestmark = pytest.mark.anyio


# --- GET /settings/platform-connections ---

async def test_platform_connections(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = Client(name="Settings Client", industry="Tech", manager_id=admin_user.id)
    db_session.add(c)
    await db_session.flush()
    account = PlatformAccount(
        client_id=c.id, platform=Platform.INSTAGRAM,
        account_name="set_insta", access_token="tok",
    )
    db_session.add(account)
    await db_session.commit()
    resp = await client.get("/api/v1/settings/platform-connections", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


async def test_platform_connections_forbidden_for_operator(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_test_user(db_session, UserRole.OPERATOR)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/api/v1/settings/platform-connections", headers=headers)
    assert resp.status_code == 403


# --- POST /settings/platform-connections/test ---

async def test_platform_connection_test(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = Client(name="Test Client", industry="Tech", manager_id=admin_user.id)
    db_session.add(c)
    await db_session.flush()
    account = PlatformAccount(
        client_id=c.id, platform=Platform.FACEBOOK,
        account_name="fb_test", access_token="tok",
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    resp = await client.post(
        "/api/v1/settings/platform-connections/test",
        json={"platform_account_id": str(account.id)},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["platform"] == "facebook"


# --- GET/PUT /settings/workflows ---

async def test_get_workflow_settings(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get("/api/v1/settings/workflows", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "approval_steps" in data


async def test_update_workflow_settings(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    payload = {
        "approval_steps": ["review"],
        "auto_publish_on_approve": True,
        "urgent_skip_enabled": False,
        "notification_channels": {"approval": ["email"]},
    }
    resp = await client.put("/api/v1/settings/workflows", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["auto_publish_on_approve"] is True
    assert data["approval_steps"] == ["review"]


async def test_update_workflow_forbidden_for_manager(client: AsyncClient, manager_auth):
    _, headers = manager_auth
    payload = {
        "approval_steps": ["review"],
        "auto_publish_on_approve": False,
        "urgent_skip_enabled": True,
        "notification_channels": {},
    }
    resp = await client.put("/api/v1/settings/workflows", json=payload, headers=headers)
    assert resp.status_code == 403


# --- GET/PUT /settings/notification-preferences ---

async def test_get_notification_preferences(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get("/api/v1/settings/notification-preferences", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "email_enabled" in data


async def test_update_notification_preferences(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    payload = {
        "email_enabled": False,
        "slack_webhook_url": "https://hooks.slack.com/test",
        "kakao_enabled": True,
        "crisis_alert": ["slack"],
        "approval_request": ["email", "slack"],
        "publish_result": ["email"],
    }
    resp = await client.put("/api/v1/settings/notification-preferences", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email_enabled"] is False
    assert data["kakao_enabled"] is True

    # Verify persisted
    resp = await client.get("/api/v1/settings/notification-preferences", headers=headers)
    assert resp.json()["data"]["slack_webhook_url"] == "https://hooks.slack.com/test"


# --- GET /settings/audit-logs ---

async def test_audit_logs(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    # Create content to generate audit logs
    from app.models.client import Client
    c = Client(name="Audit Client", industry="Tech", manager_id=admin_user.id)
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    # Create content via API (generates audit log)
    payload = {
        "client_id": str(c.id),
        "title": "Audit Test Content",
        "content_type": "feed",
        "target_platforms": ["instagram"],
    }
    await client.post("/api/v1/contents", json=payload, headers=headers)

    resp = await client.get("/api/v1/settings/audit-logs", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] >= 1
    assert body["data"][0]["entity_type"] == "content"


async def test_audit_logs_filter_entity_type(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get("/api/v1/settings/audit-logs?entity_type=content", headers=headers)
    assert resp.status_code == 200
