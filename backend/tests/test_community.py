"""Tests for Community API (8 endpoints)."""
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.comment import CommentInbox, CommentStatus, Sentiment
from app.models.content import Content, ContentType
from app.models.filter_rule import FilterAction, FilterRule, RuleType
from app.models.platform_account import Platform, PlatformAccount
from app.models.user import User, UserRole
from tests.conftest import _create_test_user


pytestmark = pytest.mark.anyio


async def _setup_community(db: AsyncSession, user: User):
    """Create client, platform account, content, and a comment."""
    client_obj = Client(name="Community Client", industry="Media", manager_id=user.id)
    db.add(client_obj)
    await db.flush()

    account = PlatformAccount(
        client_id=client_obj.id,
        platform=Platform.INSTAGRAM,
        account_name="comm_insta",
        access_token="tok",
    )
    db.add(account)
    await db.flush()

    content = Content(
        client_id=client_obj.id,
        title="Post with comments",
        content_type=ContentType.FEED,
        target_platforms=["instagram"],
        created_by=user.id,
    )
    db.add(content)
    await db.flush()

    comment = CommentInbox(
        platform_account_id=account.id,
        content_id=content.id,
        platform_comment_id="ext_123",
        author_name="TestUser",
        message="Great post!",
        sentiment=Sentiment.POSITIVE,
        sentiment_score=0.95,
        status=CommentStatus.PENDING,
        commented_at=datetime.now(timezone.utc),
    )
    db.add(comment)
    await db.commit()
    await db.refresh(client_obj)
    await db.refresh(account)
    await db.refresh(content)
    await db.refresh(comment)
    return client_obj, account, content, comment


# --- GET /community/inbox ---

async def test_list_inbox(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    await _setup_community(db_session, admin_user)
    resp = await client.get("/api/v1/community/inbox", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] >= 1
    assert body["data"][0]["author_name"] == "TestUser"


async def test_list_inbox_filter_sentiment(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    await _setup_community(db_session, admin_user)
    resp = await client.get("/api/v1/community/inbox?sentiment=positive", headers=headers)
    assert resp.status_code == 200
    for c in resp.json()["data"]:
        assert c["sentiment"] == "positive"


async def test_inbox_forbidden_for_client_role(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_test_user(db_session, UserRole.CLIENT)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/api/v1/community/inbox", headers=headers)
    assert resp.status_code == 403


# --- POST /community/{id}/reply ---

async def test_reply_to_comment(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, _, _, comment = await _setup_community(db_session, admin_user)
    resp = await client.post(
        f"/api/v1/community/{comment.id}/reply",
        json={"message": "Thank you!"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "replied"
    assert data["replied_by"] == str(admin_user.id)


async def test_reply_not_found(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.post(
        f"/api/v1/community/{uuid.uuid4()}/reply",
        json={"message": "Hi"},
        headers=headers,
    )
    assert resp.status_code == 404


# --- PATCH /community/{id}/status ---

async def test_update_comment_status(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, _, _, comment = await _setup_community(db_session, admin_user)
    resp = await client.patch(
        f"/api/v1/community/{comment.id}/status",
        json={"status": "hidden"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "hidden"


async def test_flag_comment(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    _, _, _, comment = await _setup_community(db_session, admin_user)
    resp = await client.patch(
        f"/api/v1/community/{comment.id}/status",
        json={"status": "flagged"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "flagged"


# --- GET /community/sentiment ---

async def test_sentiment_stats(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    await _setup_community(db_session, admin_user)
    resp = await client.get("/api/v1/community/sentiment", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["positive"] >= 1
    assert data["total"] >= 1


# --- Filter Rules CRUD ---

async def test_filter_rule_crud(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = Client(name="Filter Client", industry="Tech", manager_id=admin_user.id)
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    # Create
    payload = {
        "client_id": str(c.id),
        "rule_type": "keyword",
        "value": "spam",
        "action": "hide",
    }
    resp = await client.post("/api/v1/community/filter-rules", json=payload, headers=headers)
    assert resp.status_code == 201
    rule_id = resp.json()["data"]["id"]

    # List
    resp = await client.get("/api/v1/community/filter-rules", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1

    # Update
    resp = await client.put(
        f"/api/v1/community/filter-rules/{rule_id}",
        json={"action": "flag", "value": "updated_spam"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["action"] == "flag"
    assert resp.json()["data"]["value"] == "updated_spam"

    # Delete
    resp = await client.delete(f"/api/v1/community/filter-rules/{rule_id}", headers=headers)
    assert resp.status_code == 200


async def test_filter_rule_forbidden_for_operator(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_test_user(db_session, UserRole.OPERATOR)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/api/v1/community/filter-rules", headers=headers)
    assert resp.status_code == 403


async def test_delete_filter_rule_not_found(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.delete(f"/api/v1/community/filter-rules/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404
