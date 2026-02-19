"""Tests for Analytics API (5 endpoints)."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserRole
from tests.conftest import _create_test_user


pytestmark = pytest.mark.anyio


# --- GET /analytics/dashboard ---

async def test_dashboard(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "reach" in data
    assert "engagement_rate" in data
    assert "follower_change" in data
    assert "video_views" in data


async def test_dashboard_with_period(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get("/api/v1/analytics/dashboard?period=7d", headers=headers)
    assert resp.status_code == 200


# --- GET /analytics/trends ---

async def test_trends(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get("/api/v1/analytics/trends?period=7d", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 7


async def test_trends_30d(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get("/api/v1/analytics/trends?period=30d", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 30


# --- GET /analytics/content-perf ---

async def test_content_perf(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get("/api/v1/analytics/content-perf", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 5  # 5 content types
    content_types = {item["content_type"] for item in data}
    assert "feed" in content_types
    assert "reel" in content_types


# --- POST /analytics/report ---

async def test_create_report(client: AsyncClient, admin_auth):
    admin_user, headers = admin_auth
    payload = {"client_id": str(uuid.uuid4()), "period": "30d"}
    resp = await client.post("/api/v1/analytics/report", json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["data"]["status"] == "processing"


async def test_create_report_forbidden_for_operator(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_test_user(db_session, UserRole.OPERATOR)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"client_id": str(uuid.uuid4()), "period": "30d"}
    resp = await client.post("/api/v1/analytics/report", json=payload, headers=headers)
    assert resp.status_code == 403


# --- GET /analytics/report/{id} ---

async def test_get_report(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get(f"/api/v1/analytics/report/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "processing"
