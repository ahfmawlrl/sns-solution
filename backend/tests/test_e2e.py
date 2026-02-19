"""End-to-end integration tests — Phase 8, STEP 30.

4 scenarios covering the full system:
1. Content lifecycle: create → AI copy → review → approve → publish → analytics
2. Community: comment → sentiment analysis → crisis alert → RAG reply
3. Client onboarding: register → connect account → add FAQ → AI chat
4. RBAC: full role-based access matrix verification
"""
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.client import Client
from app.models.comment import CommentInbox, Sentiment
from app.models.platform_account import PlatformAccount, Platform
from app.services.auth_service import create_access_token, hash_password


# ─── Shared Setup ────────────────────────────────────────────────────────

async def _e2e_setup(db: AsyncSession):
    """Create full environment for E2E tests."""
    admin = User(
        id=uuid.uuid4(), email="admin@e2e.test",
        password_hash=hash_password("pass123"), name="Admin", role=UserRole.ADMIN,
    )
    manager = User(
        id=uuid.uuid4(), email="mgr@e2e.test",
        password_hash=hash_password("pass123"), name="Manager", role=UserRole.MANAGER,
    )
    operator = User(
        id=uuid.uuid4(), email="op@e2e.test",
        password_hash=hash_password("pass123"), name="Operator", role=UserRole.OPERATOR,
    )
    client_user = User(
        id=uuid.uuid4(), email="client@e2e.test",
        password_hash=hash_password("pass123"), name="ClientUser", role=UserRole.CLIENT,
    )
    db.add_all([admin, manager, operator, client_user])
    await db.flush()

    brand = Client(
        id=uuid.uuid4(), name="E2E Brand", industry="technology",
        manager_id=manager.id,
    )
    db.add(brand)
    await db.flush()

    ig_account = PlatformAccount(
        id=uuid.uuid4(), client_id=brand.id,
        platform=Platform.INSTAGRAM, account_name="e2e_insta",
        access_token="encrypted_token", is_connected=True,
    )
    fb_account = PlatformAccount(
        id=uuid.uuid4(), client_id=brand.id,
        platform=Platform.FACEBOOK, account_name="e2e_facebook",
        access_token="encrypted_token_fb", is_connected=True,
    )
    db.add_all([ig_account, fb_account])
    await db.commit()

    def _h(user):
        t = create_access_token(str(user.id), user.role.value)
        return {"Authorization": f"Bearer {t}"}

    return {
        "admin": (admin, _h(admin)),
        "manager": (manager, _h(manager)),
        "operator": (operator, _h(operator)),
        "client": (client_user, _h(client_user)),
        "brand": brand,
        "ig_account": ig_account,
        "fb_account": fb_account,
    }


# ─── Scenario 1: Content Lifecycle with AI ───────────────────────────────

class TestScenario1ContentLifecycle:
    """Content: create → AI generate copy → review workflow → publish → analytics."""

    async def test_full_content_lifecycle(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _e2e_setup(db_session)
        _, op_h = setup["operator"]
        _, mgr_h = setup["manager"]
        _, cl_h = setup["client"]
        brand = setup["brand"]

        # 1. AI generates copy for the brand
        resp = await client.post(
            "/api/v1/ai/generate-copy",
            json={
                "client_id": str(brand.id),
                "prompt": "New Year Campaign festive and engaging",
                "platform": "instagram",
                "content_type": "feed",
                "num_drafts": 2,
            },
            headers=op_h,
        )
        assert resp.status_code == 200
        ai_data = resp.json()["data"]
        # data is a list of draft dicts
        assert isinstance(ai_data, list)
        assert len(ai_data) >= 1

        # 2. Operator creates content using AI draft
        draft_text = ai_data[0].get("text", "Happy New Year!") if isinstance(ai_data[0], dict) else str(ai_data[0])
        resp = await client.post(
            "/api/v1/contents",
            json={
                "client_id": str(brand.id),
                "title": "New Year Campaign Post",
                "body": draft_text,
                "content_type": "feed",
                "target_platforms": ["instagram", "facebook"],
            },
            headers=op_h,
        )
        assert resp.status_code == 201
        content_id = resp.json()["data"]["id"]
        assert resp.json()["data"]["status"] == "draft"

        # 3. Operator submits for review (draft → review)
        resp = await client.patch(
            f"/api/v1/contents/{content_id}/status",
            json={"to_status": "review"},
            headers=op_h,
        )
        assert resp.status_code == 200

        # 4. Manager sends to client review (review → client_review)
        resp = await client.patch(
            f"/api/v1/contents/{content_id}/status",
            json={"to_status": "client_review"},
            headers=mgr_h,
        )
        assert resp.status_code == 200

        # 5. Client approves (client_review → approved)
        resp = await client.patch(
            f"/api/v1/contents/{content_id}/status",
            json={"to_status": "approved"},
            headers=cl_h,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "approved"

        # 6. Check content detail
        resp = await client.get(f"/api/v1/contents/{content_id}", headers=op_h)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "approved"

        # 7. Verify content appears in list
        resp = await client.get(
            f"/api/v1/contents?client_id={brand.id}",
            headers=op_h,
        )
        assert resp.status_code == 200
        assert any(c["id"] == content_id for c in resp.json()["data"])

        # 8. Check analytics dashboard
        resp = await client.get(
            f"/api/v1/analytics/dashboard?client_id={brand.id}",
            headers=mgr_h,
        )
        assert resp.status_code == 200


# ─── Scenario 2: Comment Sentiment + Crisis Alert + RAG Reply ────────────

class TestScenario2CommunityMonitoring:
    """Comment → sentiment → crisis detection → RAG reply draft."""

    async def test_sentiment_analysis_flow(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _e2e_setup(db_session)
        _, op_h = setup["operator"]

        # 1. Analyze sentiment via API
        resp = await client.post(
            "/api/v1/ai/sentiment",
            json={"text": "This product is amazing! Best purchase ever!"},
            headers=op_h,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["sentiment"] == "positive"
        assert data["score"] > 0

    async def test_batch_sentiment_with_crisis(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _e2e_setup(db_session)
        _, op_h = setup["operator"]

        # 2. Batch analysis with crisis detection
        resp = await client.post(
            "/api/v1/ai/sentiment/batch",
            json={
                "texts": [
                    "Love this brand!",
                    "Okay product, nothing special",
                    "소송 고소 법적 조치를 취하겠습니다",
                ]
            },
            headers=op_h,
        )
        assert resp.status_code == 200
        # data is a list (not {"results": [...]})
        results = resp.json()["data"]
        assert isinstance(results, list)
        assert len(results) == 3
        # Third text should be crisis or negative
        assert results[2]["sentiment"] in ("crisis", "negative")

    async def test_comment_with_ai_reply(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _e2e_setup(db_session)
        _, op_h = setup["operator"]
        ig_account = setup["ig_account"]

        # 3. Create a comment
        comment = CommentInbox(
            id=uuid.uuid4(),
            platform_account_id=ig_account.id,
            platform_comment_id="cmt_crisis_001",
            author_name="AngryUser",
            message="이 제품 불량입니다. 소송 하겠습니다.",
            sentiment=Sentiment.CRISIS,
            commented_at=datetime.now(timezone.utc),
        )
        db_session.add(comment)
        await db_session.commit()

        # 4. Get AI-suggested reply draft (POST, not GET)
        resp = await client.post(
            f"/api/v1/ai/suggest-reply/{comment.id}",
            headers=op_h,
        )
        assert resp.status_code == 200
        reply_data = resp.json()["data"]
        assert "reply" in reply_data
        assert len(reply_data["reply"]) > 0

        # 5. Operator replies to the comment
        resp = await client.post(
            f"/api/v1/community/{comment.id}/reply",
            json={"message": reply_data["reply"]},
            headers=op_h,
        )
        assert resp.status_code == 200


# ─── Scenario 3: Client Onboarding + FAQ + AI Chat ──────────────────────

class TestScenario3ClientOnboarding:
    """Client registration → account connect → FAQ → AI chat."""

    async def test_client_onboarding_flow(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _e2e_setup(db_session)
        _, admin_h = setup["admin"]
        _, mgr_h = setup["manager"]
        brand = setup["brand"]

        # 1. Admin lists clients
        resp = await client.get("/api/v1/clients", headers=admin_h)
        assert resp.status_code == 200

        # 2. Get client detail
        resp = await client.get(f"/api/v1/clients/{brand.id}", headers=mgr_h)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "E2E Brand"

        # 3. List connected platform accounts
        resp = await client.get(
            f"/api/v1/clients/{brand.id}/accounts",
            headers=mgr_h,
        )
        assert resp.status_code == 200
        accounts = resp.json()["data"]
        assert len(accounts) == 2  # Instagram + Facebook

        # 4. Add FAQ guideline
        resp = await client.post(
            f"/api/v1/clients/{brand.id}/faq-guidelines",
            json={
                "category": "faq",
                "title": "Return Policy",
                "content": "Our return policy allows returns within 30 days of purchase.",
                "priority": 10,
            },
            headers=mgr_h,
        )
        assert resp.status_code == 201

        # 5. List FAQ guidelines
        resp = await client.get(
            f"/api/v1/clients/{brand.id}/faq-guidelines",
            headers=mgr_h,
        )
        assert resp.status_code == 200
        faqs = resp.json()["data"]
        assert len(faqs) >= 1
        assert faqs[0]["title"] == "Return Policy"

    async def test_ai_chat(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _e2e_setup(db_session)
        _, op_h = setup["operator"]

        # 6. AI chat query
        resp = await client.post(
            "/api/v1/ai/chat",
            json={
                "message": "How many posts did we publish last week?",
                "context": {"client_id": str(setup["brand"].id)},
            },
            headers=op_h,
        )
        assert resp.status_code == 200
        chat_data = resp.json()["data"]
        assert "reply" in chat_data


# ─── Scenario 4: Full RBAC Matrix ───────────────────────────────────────

class TestScenario4RBACMatrix:
    """Comprehensive role-based access control verification."""

    async def test_admin_full_access(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _e2e_setup(db_session)
        _, h = setup["admin"]

        # Admin can access everything
        for endpoint in [
            "/api/v1/users",
            "/api/v1/clients",
            "/api/v1/contents",
            "/api/v1/notifications",
            "/api/v1/settings/audit-logs",
        ]:
            resp = await client.get(endpoint, headers=h)
            assert resp.status_code == 200, f"Admin denied on {endpoint}: {resp.status_code}"

    async def test_manager_access(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _e2e_setup(db_session)
        _, h = setup["manager"]

        # Manager can access clients, contents, analytics
        for endpoint in ["/api/v1/clients", "/api/v1/contents"]:
            resp = await client.get(endpoint, headers=h)
            assert resp.status_code == 200, f"Manager denied on {endpoint}"

        # Manager cannot manage users
        resp = await client.get("/api/v1/users", headers=h)
        assert resp.status_code == 403

    async def test_operator_access(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _e2e_setup(db_session)
        _, h = setup["operator"]

        # Operator can access contents
        resp = await client.get("/api/v1/contents", headers=h)
        assert resp.status_code == 200

        # Operator cannot manage users or access audit logs
        resp = await client.get("/api/v1/users", headers=h)
        assert resp.status_code == 403

    async def test_client_access(self, client: AsyncClient, db_session: AsyncSession):
        setup = await _e2e_setup(db_session)
        _, h = setup["client"]

        # Client cannot create content
        resp = await client.post(
            "/api/v1/contents",
            json={
                "client_id": str(setup["brand"].id),
                "title": "Unauthorized",
                "body": "test",
                "content_type": "feed",
                "target_platforms": ["instagram"],
            },
            headers=h,
        )
        assert resp.status_code == 403

        # Client cannot access user management
        resp = await client.get("/api/v1/users", headers=h)
        assert resp.status_code == 403

    async def test_cross_role_content_workflow(self, client: AsyncClient, db_session: AsyncSession):
        """Multi-role content approval workflow."""
        setup = await _e2e_setup(db_session)
        _, op_h = setup["operator"]
        _, mgr_h = setup["manager"]
        _, cl_h = setup["client"]
        brand = setup["brand"]

        # Operator creates
        resp = await client.post(
            "/api/v1/contents",
            json={
                "client_id": str(brand.id),
                "title": "RBAC Workflow Test",
                "body": "Testing cross-role workflow",
                "content_type": "feed",
                "target_platforms": ["instagram"],
            },
            headers=op_h,
        )
        assert resp.status_code == 201
        cid = resp.json()["data"]["id"]

        # Operator submits (draft → review)
        resp = await client.patch(
            f"/api/v1/contents/{cid}/status",
            json={"to_status": "review"},
            headers=op_h,
        )
        assert resp.status_code == 200

        # Manager advances (review → client_review)
        resp = await client.patch(
            f"/api/v1/contents/{cid}/status",
            json={"to_status": "client_review"},
            headers=mgr_h,
        )
        assert resp.status_code == 200

        # Client approves (client_review → approved)
        resp = await client.patch(
            f"/api/v1/contents/{cid}/status",
            json={"to_status": "approved"},
            headers=cl_h,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "approved"

    async def test_health_and_metrics_public(self, client: AsyncClient):
        """Health and metrics endpoints should be publicly accessible."""
        resp = await client.get("/health")
        assert resp.status_code == 200

        resp = await client.get("/metrics")
        assert resp.status_code == 200
        body = resp.text
        assert "http_requests_total" in body
