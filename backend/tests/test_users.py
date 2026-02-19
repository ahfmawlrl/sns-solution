"""Tests for Users API (8 endpoints)."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from tests.conftest import _create_test_user


pytestmark = pytest.mark.anyio


# --- GET /api/v1/users (admin only) ---

async def test_list_users_as_admin(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    resp = await client.get("/api/v1/users", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert isinstance(body["data"], list)
    assert body["pagination"]["total"] >= 1


async def test_list_users_forbidden_for_operator(client: AsyncClient, operator_auth):
    _, headers = operator_auth
    resp = await client.get("/api/v1/users", headers=headers)
    assert resp.status_code == 403


async def test_list_users_filter_by_role(client: AsyncClient, admin_auth, db_session: AsyncSession):
    _, headers = admin_auth
    await _create_test_user(db_session, UserRole.OPERATOR)
    resp = await client.get("/api/v1/users?role=operator", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert all(u["role"] == "operator" for u in data)


async def test_list_users_search(client: AsyncClient, admin_auth, db_session: AsyncSession):
    _, headers = admin_auth
    await _create_test_user(db_session, UserRole.OPERATOR, email="searchme@test.com")
    resp = await client.get("/api/v1/users?search=searchme", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


# --- POST /api/v1/users (admin only) ---

async def test_create_user(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    payload = {
        "email": "newuser@test.com",
        "password": "securepass123",
        "name": "New User",
        "role": "operator",
    }
    resp = await client.post("/api/v1/users", json=payload, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["email"] == "newuser@test.com"
    assert body["data"]["role"] == "operator"


async def test_create_user_forbidden_for_manager(client: AsyncClient, manager_auth):
    _, headers = manager_auth
    payload = {
        "email": "blocked@test.com",
        "password": "securepass123",
        "name": "Blocked",
        "role": "operator",
    }
    resp = await client.post("/api/v1/users", json=payload, headers=headers)
    assert resp.status_code == 403


# --- GET /api/v1/users/{id} (admin, manager) ---

async def test_get_user_by_id(client: AsyncClient, admin_auth, db_session: AsyncSession):
    _, headers = admin_auth
    target, _ = await _create_test_user(db_session, UserRole.OPERATOR)
    resp = await client.get(f"/api/v1/users/{target.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == str(target.id)


async def test_get_user_not_found(client: AsyncClient, admin_auth):
    _, headers = admin_auth
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/users/{fake_id}", headers=headers)
    assert resp.status_code == 404


async def test_get_user_as_manager(client: AsyncClient, manager_auth, db_session: AsyncSession):
    _, headers = manager_auth
    target, _ = await _create_test_user(db_session, UserRole.OPERATOR)
    resp = await client.get(f"/api/v1/users/{target.id}", headers=headers)
    assert resp.status_code == 200


async def test_get_user_forbidden_for_operator(client: AsyncClient, operator_auth, db_session: AsyncSession):
    _, headers = operator_auth
    target, _ = await _create_test_user(db_session, UserRole.ADMIN)
    resp = await client.get(f"/api/v1/users/{target.id}", headers=headers)
    assert resp.status_code == 403


# --- PUT /api/v1/users/{id} (admin only) ---

async def test_update_user(client: AsyncClient, admin_auth, db_session: AsyncSession):
    _, headers = admin_auth
    target, _ = await _create_test_user(db_session, UserRole.OPERATOR)
    resp = await client.put(
        f"/api/v1/users/{target.id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Updated Name"


# --- PATCH /api/v1/users/{id}/role (admin only) ---

async def test_change_role(client: AsyncClient, admin_auth, db_session: AsyncSession):
    _, headers = admin_auth
    target, _ = await _create_test_user(db_session, UserRole.OPERATOR)
    resp = await client.patch(
        f"/api/v1/users/{target.id}/role",
        json={"role": "manager"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "manager"


# --- PATCH /api/v1/users/{id}/active (admin only) ---

async def test_toggle_active(client: AsyncClient, admin_auth, db_session: AsyncSession):
    _, headers = admin_auth
    target, _ = await _create_test_user(db_session, UserRole.OPERATOR)
    resp = await client.patch(
        f"/api/v1/users/{target.id}/active",
        json={"is_active": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is False


# --- PUT /api/v1/users/me/profile (authenticated) ---

async def test_update_my_profile(client: AsyncClient, operator_auth):
    _, headers = operator_auth
    resp = await client.put(
        "/api/v1/users/me/profile",
        json={"name": "My New Name"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "My New Name"


# --- PUT /api/v1/users/me/password (authenticated) ---

async def test_change_my_password(client: AsyncClient, operator_auth):
    _, headers = operator_auth
    resp = await client.put(
        "/api/v1/users/me/password",
        json={"current_password": "testpass123", "new_password": "newpass12345"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Password changed"


async def test_change_password_wrong_current(client: AsyncClient, operator_auth):
    _, headers = operator_auth
    resp = await client.put(
        "/api/v1/users/me/password",
        json={"current_password": "wrongpass", "new_password": "newpass12345"},
        headers=headers,
    )
    assert resp.status_code == 400
