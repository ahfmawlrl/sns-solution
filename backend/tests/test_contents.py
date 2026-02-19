"""Tests for Contents API (10 endpoints) + workflow."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.content import Content, ContentStatus, ContentType
from app.models.user import User, UserRole
from tests.conftest import _create_test_user


pytestmark = pytest.mark.anyio


async def _setup_client(db: AsyncSession, manager: User) -> Client:
    """Create a client for content tests."""
    c = Client(name="Content Test Client", industry="Media", manager_id=manager.id)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def _create_content(
    db: AsyncSession, client_obj: Client, creator: User,
    status: ContentStatus = ContentStatus.DRAFT,
) -> Content:
    """Create a test content."""
    content = Content(
        client_id=client_obj.id,
        title=f"Test Content {uuid.uuid4().hex[:6]}",
        body="Test body",
        content_type=ContentType.FEED,
        target_platforms=["instagram"],
        status=status,
        created_by=creator.id,
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return content


# --- POST /api/v1/contents ---

async def test_create_content(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    payload = {
        "client_id": str(c.id),
        "title": "New Post",
        "body": "Hello world",
        "content_type": "feed",
        "target_platforms": ["instagram", "facebook"],
        "hashtags": ["#test"],
    }
    resp = await client.post("/api/v1/contents", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["title"] == "New Post"
    assert data["status"] == "draft"
    assert data["created_by"] == str(admin_user.id)


async def test_create_content_forbidden_for_client_role(client: AsyncClient, db_session: AsyncSession):
    user, token = await _create_test_user(db_session, UserRole.CLIENT)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "client_id": str(uuid.uuid4()),
        "title": "Blocked",
        "content_type": "feed",
        "target_platforms": ["instagram"],
    }
    resp = await client.post("/api/v1/contents", json=payload, headers=headers)
    assert resp.status_code == 403


# --- GET /api/v1/contents ---

async def test_list_contents(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    await _create_content(db_session, c, admin_user)
    resp = await client.get("/api/v1/contents", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] >= 1


async def test_list_contents_filter_by_status(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    await _create_content(db_session, c, admin_user, ContentStatus.DRAFT)
    await _create_content(db_session, c, admin_user, ContentStatus.REVIEW)
    resp = await client.get("/api/v1/contents?status=draft", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["data"]:
        assert item["status"] == "draft"


# --- GET /api/v1/contents/{id} ---

async def test_get_content(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user)
    resp = await client.get(f"/api/v1/contents/{content.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == str(content.id)


async def test_get_content_not_found(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get(f"/api/v1/contents/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


# --- PUT /api/v1/contents/{id} ---

async def test_update_content(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user)
    resp = await client.put(
        f"/api/v1/contents/{content.id}",
        json={"title": "Updated Title"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "Updated Title"


# --- DELETE /api/v1/contents/{id} ---

async def test_delete_draft_content(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user, ContentStatus.DRAFT)
    resp = await client.delete(f"/api/v1/contents/{content.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Content deleted"


async def test_delete_non_draft_fails(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user, ContentStatus.REVIEW)
    resp = await client.delete(f"/api/v1/contents/{content.id}", headers=headers)
    assert resp.status_code == 400


# --- PATCH /api/v1/contents/{id}/status (workflow) ---

async def test_operator_draft_to_review(client: AsyncClient, db_session: AsyncSession):
    admin_user, _ = await _create_test_user(db_session, UserRole.ADMIN)
    operator, op_token = await _create_test_user(db_session, UserRole.OPERATOR)
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, operator, ContentStatus.DRAFT)
    headers = {"Authorization": f"Bearer {op_token}"}
    resp = await client.patch(
        f"/api/v1/contents/{content.id}/status",
        json={"to_status": "review"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "review"


async def test_manager_review_to_client_review(client: AsyncClient, db_session: AsyncSession):
    admin_user, _ = await _create_test_user(db_session, UserRole.ADMIN)
    manager, mgr_token = await _create_test_user(db_session, UserRole.MANAGER)
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user, ContentStatus.REVIEW)
    headers = {"Authorization": f"Bearer {mgr_token}"}
    resp = await client.patch(
        f"/api/v1/contents/{content.id}/status",
        json={"to_status": "client_review", "comment": "Looks good"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "client_review"


async def test_client_approve(client: AsyncClient, db_session: AsyncSession):
    admin_user, _ = await _create_test_user(db_session, UserRole.ADMIN)
    client_user, cl_token = await _create_test_user(db_session, UserRole.CLIENT)
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user, ContentStatus.CLIENT_REVIEW)
    headers = {"Authorization": f"Bearer {cl_token}"}
    resp = await client.patch(
        f"/api/v1/contents/{content.id}/status",
        json={"to_status": "approved"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "approved"
    assert data["approved_by"] == str(client_user.id)


async def test_client_reject(client: AsyncClient, db_session: AsyncSession):
    admin_user, _ = await _create_test_user(db_session, UserRole.ADMIN)
    _, cl_token = await _create_test_user(db_session, UserRole.CLIENT)
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user, ContentStatus.CLIENT_REVIEW)
    headers = {"Authorization": f"Bearer {cl_token}"}
    resp = await client.patch(
        f"/api/v1/contents/{content.id}/status",
        json={"to_status": "rejected", "comment": "Needs revision"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "rejected"


async def test_invalid_transition_fails(client: AsyncClient, db_session: AsyncSession):
    """Operator cannot move from draft to approved directly."""
    admin_user, _ = await _create_test_user(db_session, UserRole.ADMIN)
    operator, op_token = await _create_test_user(db_session, UserRole.OPERATOR)
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, operator, ContentStatus.DRAFT)
    headers = {"Authorization": f"Bearer {op_token}"}
    resp = await client.patch(
        f"/api/v1/contents/{content.id}/status",
        json={"to_status": "approved"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_manager_reject_to_draft(client: AsyncClient, db_session: AsyncSession):
    admin_user, _ = await _create_test_user(db_session, UserRole.ADMIN)
    manager, mgr_token = await _create_test_user(db_session, UserRole.MANAGER)
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user, ContentStatus.REJECTED)
    headers = {"Authorization": f"Bearer {mgr_token}"}
    resp = await client.patch(
        f"/api/v1/contents/{content.id}/status",
        json={"to_status": "draft"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "draft"


# --- GET /api/v1/contents/{id}/approvals ---

async def test_approval_history(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user, ContentStatus.DRAFT)

    # Move draft → review (as admin)
    await client.patch(
        f"/api/v1/contents/{content.id}/status",
        json={"to_status": "review"},
        headers=headers,
    )
    resp = await client.get(f"/api/v1/contents/{content.id}/approvals", headers=headers)
    assert resp.status_code == 200
    approvals = resp.json()["data"]
    assert len(approvals) >= 1
    assert approvals[0]["from_status"] == "draft"
    assert approvals[0]["to_status"] == "review"


# --- POST /api/v1/contents/{id}/upload ---

async def test_upload_url(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user)
    resp = await client.post(
        f"/api/v1/contents/{content.id}/upload",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert "upload_url" in data
    assert "file_key" in data


# --- GET /api/v1/contents/{id}/publishing-logs ---

async def test_publishing_logs_empty(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    content = await _create_content(db_session, c, admin_user)
    resp = await client.get(f"/api/v1/contents/{content.id}/publishing-logs", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == []


# --- GET /api/v1/contents/calendar ---

async def test_calendar_view(client: AsyncClient, admin_auth, db_session: AsyncSession):
    from datetime import datetime, timezone
    admin_user, headers = admin_auth
    c = await _setup_client(db_session, admin_user)
    # Create content with scheduled_at
    content = Content(
        client_id=c.id,
        title="Scheduled Post",
        content_type=ContentType.FEED,
        target_platforms=["instagram"],
        created_by=admin_user.id,
        scheduled_at=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(content)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/contents/calendar?start=2026-03-01&end=2026-03-31",
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1
