"""Tests for Clients API (13 endpoints)."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client, ClientStatus
from app.models.user import User, UserRole
from tests.conftest import _create_test_user


pytestmark = pytest.mark.anyio


async def _create_test_client(db: AsyncSession, manager: User) -> Client:
    """Helper to create a test client."""
    client_obj = Client(
        name=f"Test Client {uuid.uuid4().hex[:6]}",
        industry="Tech",
        manager_id=manager.id,
    )
    db.add(client_obj)
    await db.commit()
    await db.refresh(client_obj)
    return client_obj


# --- GET /api/v1/clients ---

async def test_list_clients(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    await _create_test_client(db_session, admin_user)
    resp = await client.get("/api/v1/clients", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert isinstance(body["data"], list)
    assert body["pagination"]["total"] >= 1


async def test_list_clients_filter_by_industry(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    await _create_test_client(db_session, admin_user)
    resp = await client.get("/api/v1/clients?industry=Tech", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


async def test_list_clients_search(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = Client(name="UniqueSearchName", industry="Search", manager_id=admin_user.id)
    db_session.add(c)
    await db_session.commit()
    resp = await client.get("/api/v1/clients?search=UniqueSearch", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


# --- POST /api/v1/clients (admin, manager) ---

async def test_create_client(client: AsyncClient, admin_auth):
    admin_user, headers = admin_auth
    payload = {
        "name": "New Client",
        "industry": "Finance",
        "manager_id": str(admin_user.id),
    }
    resp = await client.post("/api/v1/clients", json=payload, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["name"] == "New Client"
    assert body["data"]["industry"] == "Finance"


async def test_create_client_as_manager(client: AsyncClient, manager_auth):
    manager_user, headers = manager_auth
    payload = {
        "name": "Manager Client",
        "industry": "Media",
        "manager_id": str(manager_user.id),
    }
    resp = await client.post("/api/v1/clients", json=payload, headers=headers)
    assert resp.status_code == 201


async def test_create_client_forbidden_for_operator(client: AsyncClient, operator_auth):
    user, headers = operator_auth
    payload = {
        "name": "Blocked Client",
        "industry": "Tech",
        "manager_id": str(user.id),
    }
    resp = await client.post("/api/v1/clients", json=payload, headers=headers)
    assert resp.status_code == 403


# --- GET /api/v1/clients/{id} ---

async def test_get_client(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _create_test_client(db_session, admin_user)
    resp = await client.get(f"/api/v1/clients/{c.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == str(c.id)


async def test_get_client_not_found(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get(f"/api/v1/clients/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


# --- PUT /api/v1/clients/{id} (admin, manager) ---

async def test_update_client(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _create_test_client(db_session, admin_user)
    resp = await client.put(
        f"/api/v1/clients/{c.id}",
        json={"name": "Updated Client Name"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Updated Client Name"


# --- PATCH /api/v1/clients/{id}/status ---

async def test_change_client_status(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _create_test_client(db_session, admin_user)
    resp = await client.patch(
        f"/api/v1/clients/{c.id}/status",
        json={"status": "paused"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "paused"


# --- PUT /api/v1/clients/{id}/brand-guidelines ---

async def test_update_brand_guidelines(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _create_test_client(db_session, admin_user)
    resp = await client.put(
        f"/api/v1/clients/{c.id}/brand-guidelines",
        json={"tone": "friendly", "color_palette": ["#FF0000", "#00FF00"]},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["brand_guidelines"]["tone"] == "friendly"


# --- Platform Accounts ---

async def test_add_and_list_accounts(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _create_test_client(db_session, admin_user)

    # Add account
    payload = {
        "platform": "instagram",
        "account_name": "test_insta",
        "access_token": "tok123",
    }
    resp = await client.post(f"/api/v1/clients/{c.id}/accounts", json=payload, headers=headers)
    assert resp.status_code == 201
    account_id = resp.json()["data"]["id"]

    # List accounts
    resp = await client.get(f"/api/v1/clients/{c.id}/accounts", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1

    # Delete account
    resp = await client.delete(f"/api/v1/clients/{c.id}/accounts/{account_id}", headers=headers)
    assert resp.status_code == 200


async def test_add_account_client_not_found(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    payload = {
        "platform": "facebook",
        "account_name": "fb_account",
        "access_token": "tok456",
    }
    resp = await client.post(f"/api/v1/clients/{uuid.uuid4()}/accounts", json=payload, headers=headers)
    assert resp.status_code == 404


async def test_delete_account_not_found(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.delete(
        f"/api/v1/clients/{uuid.uuid4()}/accounts/{uuid.uuid4()}", headers=headers
    )
    assert resp.status_code == 404


# --- FAQ/Guidelines ---

async def test_faq_crud(client: AsyncClient, admin_auth, db_session: AsyncSession):
    admin_user, headers = admin_auth
    c = await _create_test_client(db_session, admin_user)

    # Create FAQ
    payload = {
        "category": "faq",
        "title": "What is SNS?",
        "content": "Social networking service.",
        "tags": ["general"],
        "priority": 1,
    }
    resp = await client.post(f"/api/v1/clients/{c.id}/faq-guidelines", json=payload, headers=headers)
    assert resp.status_code == 201
    faq_id = resp.json()["data"]["id"]

    # List FAQs
    resp = await client.get(f"/api/v1/clients/{c.id}/faq-guidelines", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1

    # Update FAQ
    resp = await client.put(
        f"/api/v1/clients/{c.id}/faq-guidelines/{faq_id}",
        json={"title": "Updated FAQ Title"},
        headers=headers,
    )
    assert resp.status_code == 200, f"FAQ update failed: {resp.json()}"
    assert resp.json()["data"]["title"] == "Updated FAQ Title"

    # Delete FAQ
    resp = await client.delete(f"/api/v1/clients/{c.id}/faq-guidelines/{faq_id}", headers=headers)
    assert resp.status_code == 200


async def test_create_faq_client_not_found(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    payload = {
        "category": "faq",
        "title": "Orphan FAQ",
        "content": "No parent client.",
    }
    resp = await client.post(
        f"/api/v1/clients/{uuid.uuid4()}/faq-guidelines", json=payload, headers=headers
    )
    assert resp.status_code == 404


async def test_delete_faq_not_found(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.delete(
        f"/api/v1/clients/{uuid.uuid4()}/faq-guidelines/{uuid.uuid4()}", headers=headers
    )
    assert resp.status_code == 404
