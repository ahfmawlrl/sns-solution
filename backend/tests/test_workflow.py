"""End-to-end workflow integration tests.

Scenario 1: Content lifecycle — create → review → client_review → approve → publish
Scenario 2: Community — comment with sentiment analysis flow
Scenario 3: RBAC — role-based access verification
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.client import Client
from app.models.content import Content, ContentStatus, ContentType
from app.models.comment import CommentInbox, Sentiment
from app.models.platform_account import PlatformAccount, Platform
from app.services.auth_service import create_access_token, hash_password


# ─── Helpers ─────────────────────────────────────────────────────────────

async def _create_full_setup(db: AsyncSession):
    """Create admin, manager, operator, client users + a client entity + platform account."""
    admin = User(
        id=uuid.uuid4(), email="admin@workflow.test",
        password_hash=hash_password("pass123"), name="Admin", role=UserRole.ADMIN,
    )
    manager = User(
        id=uuid.uuid4(), email="mgr@workflow.test",
        password_hash=hash_password("pass123"), name="Manager", role=UserRole.MANAGER,
    )
    operator = User(
        id=uuid.uuid4(), email="op@workflow.test",
        password_hash=hash_password("pass123"), name="Operator", role=UserRole.OPERATOR,
    )
    client_user = User(
        id=uuid.uuid4(), email="client@workflow.test",
        password_hash=hash_password("pass123"), name="ClientUser", role=UserRole.CLIENT,
    )
    db.add_all([admin, manager, operator, client_user])
    await db.flush()

    client_entity = Client(
        id=uuid.uuid4(), name="Test Brand", industry="tech",
        manager_id=manager.id,
    )
    db.add(client_entity)
    await db.flush()

    platform_account = PlatformAccount(
        id=uuid.uuid4(), client_id=client_entity.id,
        platform=Platform.INSTAGRAM,
        account_name="testbrand_ig",
        access_token="encrypted_test_token",
        is_connected=True,
    )
    db.add(platform_account)
    await db.commit()

    def _headers(user):
        token = create_access_token(str(user.id), user.role.value)
        return {"Authorization": f"Bearer {token}"}

    return {
        "admin": (admin, _headers(admin)),
        "manager": (manager, _headers(manager)),
        "operator": (operator, _headers(operator)),
        "client": (client_user, _headers(client_user)),
        "client_entity": client_entity,
        "platform_account": platform_account,
    }


# ─── Scenario 1: Content Lifecycle ──────────────────────────────────────

class TestContentWorkflow:
    """Full content lifecycle: create → status changes → final state."""

    async def test_create_content(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _create_full_setup(db_session)
        _, op_headers = setup["operator"]
        client_entity = setup["client_entity"]

        # 1. Operator creates draft content
        resp = await client.post(
            "/api/v1/contents",
            json={
                "client_id": str(client_entity.id),
                "title": "Summer Campaign",
                "body": "New summer products are here!",
                "content_type": "feed",
                "target_platforms": ["instagram"],
            },
            headers=op_headers,
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == "draft"
        content_id = data["id"]

        # 2. Operator submits for review (draft → review)
        resp = await client.patch(
            f"/api/v1/contents/{content_id}/status",
            json={"to_status": "review"},
            headers=op_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "review"

        # 3. Manager moves to client review (review → client_review)
        _, mgr_headers = setup["manager"]
        resp = await client.patch(
            f"/api/v1/contents/{content_id}/status",
            json={"to_status": "client_review"},
            headers=mgr_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "client_review"

        # 4. Client approves (client_review → approved)
        _, client_headers = setup["client"]
        resp = await client.patch(
            f"/api/v1/contents/{content_id}/status",
            json={"to_status": "approved"},
            headers=client_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "approved"

    async def test_content_rejection_and_resubmit(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _create_full_setup(db_session)
        _, op_headers = setup["operator"]
        _, mgr_headers = setup["manager"]
        client_entity = setup["client_entity"]

        # Create and submit
        resp = await client.post(
            "/api/v1/contents",
            json={
                "client_id": str(client_entity.id),
                "title": "Rejected Content",
                "body": "This will be rejected",
                "content_type": "feed",
                "target_platforms": ["instagram"],
            },
            headers=op_headers,
        )
        content_id = resp.json()["data"]["id"]

        await client.patch(
            f"/api/v1/contents/{content_id}/status",
            json={"to_status": "review"},
            headers=op_headers,
        )

        # Manager rejects (review → rejected)
        resp = await client.patch(
            f"/api/v1/contents/{content_id}/status",
            json={"to_status": "rejected", "comment": "Need more details"},
            headers=mgr_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "rejected"

        # Manager reverts (rejected → draft)
        resp = await client.patch(
            f"/api/v1/contents/{content_id}/status",
            json={"to_status": "draft"},
            headers=mgr_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "draft"

        # Operator can resubmit
        resp = await client.patch(
            f"/api/v1/contents/{content_id}/status",
            json={"to_status": "review"},
            headers=op_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "review"

    async def test_content_list_with_filters(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _create_full_setup(db_session)
        _, op_headers = setup["operator"]
        client_entity = setup["client_entity"]

        # Create 2 contents
        for title in ["Content A", "Content B"]:
            await client.post(
                "/api/v1/contents",
                json={
                    "client_id": str(client_entity.id),
                    "title": title,
                    "body": "test body",
                    "content_type": "feed",
                    "target_platforms": ["instagram"],
                },
                headers=op_headers,
            )

        # List all
        resp = await client.get("/api/v1/contents", headers=op_headers)
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) >= 2

        # Filter by client
        resp = await client.get(
            f"/api/v1/contents?client_id={client_entity.id}",
            headers=op_headers,
        )
        assert resp.status_code == 200


# ─── Scenario 2: Community Monitoring ────────────────────────────────────

class TestCommunityWorkflow:
    """Comment with sentiment classification flow."""

    async def test_comment_reply_flow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _create_full_setup(db_session)
        _, op_headers = setup["operator"]
        client_entity = setup["client_entity"]
        platform_account = setup["platform_account"]

        # Create a comment in the inbox
        from datetime import datetime, timezone
        comment = CommentInbox(
            id=uuid.uuid4(),
            platform_account_id=platform_account.id,
            platform_comment_id="cmt_001",
            author_name="Customer1",
            message="Great product! Love it!",
            sentiment=Sentiment.POSITIVE,
            commented_at=datetime.now(timezone.utc),
        )
        db_session.add(comment)
        await db_session.commit()

        # Get inbox
        resp = await client.get(
            f"/api/v1/community/inbox?platform_account_id={platform_account.id}",
            headers=op_headers,
        )
        assert resp.status_code == 200

        # Reply to the comment
        resp = await client.post(
            f"/api/v1/community/{comment.id}/reply",
            json={"message": "Thank you for your kind feedback!"},
            headers=op_headers,
        )
        assert resp.status_code == 200


# ─── Scenario 3: RBAC ────────────────────────────────────────────────────

class TestRBACWorkflow:
    """Verify role-based access control across endpoints."""

    async def test_admin_can_list_users(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _create_full_setup(db_session)
        _, admin_headers = setup["admin"]
        resp = await client.get("/api/v1/users", headers=admin_headers)
        assert resp.status_code == 200

    async def test_operator_cannot_list_users(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _create_full_setup(db_session)
        _, op_headers = setup["operator"]
        resp = await client.get("/api/v1/users", headers=op_headers)
        assert resp.status_code == 403

    async def test_client_cannot_create_content(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _create_full_setup(db_session)
        _, client_headers = setup["client"]
        resp = await client.post(
            "/api/v1/contents",
            json={
                "client_id": str(setup["client_entity"].id),
                "title": "Unauthorized",
                "body": "test",
                "content_type": "feed",
                "target_platforms": ["instagram"],
            },
            headers=client_headers,
        )
        assert resp.status_code == 403

    async def test_unauthenticated_access_denied(self, client: AsyncClient):
        resp = await client.get("/api/v1/users")
        assert resp.status_code in (401, 403)

    async def test_manager_can_access_clients(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _create_full_setup(db_session)
        _, mgr_headers = setup["manager"]
        resp = await client.get("/api/v1/clients", headers=mgr_headers)
        assert resp.status_code == 200

    async def test_admin_can_access_audit_logs(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _create_full_setup(db_session)
        _, admin_headers = setup["admin"]
        resp = await client.get("/api/v1/settings/audit-logs", headers=admin_headers)
        assert resp.status_code == 200


# ─── Scenario 4: Analytics ───────────────────────────────────────────────

class TestAnalyticsWorkflow:
    """Analytics data access."""

    async def test_dashboard_kpi(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _create_full_setup(db_session)
        _, mgr_headers = setup["manager"]
        resp = await client.get(
            f"/api/v1/analytics/dashboard?client_id={setup['client_entity'].id}",
            headers=mgr_headers,
        )
        assert resp.status_code == 200

    async def test_trend_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        setup = await _create_full_setup(db_session)
        _, mgr_headers = setup["manager"]
        resp = await client.get(
            f"/api/v1/analytics/trends?client_id={setup['client_entity'].id}&metric=followers&period=7d",
            headers=mgr_headers,
        )
        assert resp.status_code == 200
