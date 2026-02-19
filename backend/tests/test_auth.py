"""Auth service and API tests."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.config import settings
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.utils.encryption import TokenEncryptor


# --- Password hashing ---

def test_hash_and_verify_password():
    password = "SecurePass123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False


# --- JWT tokens ---

def test_create_and_decode_access_token():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, "admin", ["client-1", "client-2"])
    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "admin"
    assert payload["client_ids"] == ["client-1", "client-2"]


def test_access_token_expires():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, "operator")
    payload = decode_access_token(token)
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    # Token should expire within ~30 minutes
    assert (exp - now).total_seconds() < 1810
    assert (exp - now).total_seconds() > 1790


def test_refresh_token_is_uuid():
    token = create_refresh_token()
    uuid.UUID(token)  # Raises if not valid UUID


def test_expired_token_raises():
    payload = {
        "sub": str(uuid.uuid4()),
        "role": "admin",
        "client_ids": [],
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(Exception):
        decode_access_token(expired_token)


# --- AES-256-GCM encryption ---

def test_encryption_roundtrip():
    # Generate a valid 32-byte hex key
    key_hex = "a" * 64  # 32 bytes in hex
    encryptor = TokenEncryptor(key_hex)
    original = "oauth-access-token-here"
    encrypted = encryptor.encrypt(original)
    assert encrypted != original
    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == original


def test_encryption_different_nonce():
    key_hex = "b" * 64
    encryptor = TokenEncryptor(key_hex)
    text = "same-text"
    enc1 = encryptor.encrypt(text)
    enc2 = encryptor.encrypt(text)
    assert enc1 != enc2  # Different nonce each time
    assert encryptor.decrypt(enc1) == text
    assert encryptor.decrypt(enc2) == text


# --- Auth API endpoints ---

@pytest.mark.asyncio
async def test_login_no_user(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@test.com",
        "password": "password",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403  # No Bearer token


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    response = await client.get("/api/v1/auth/me", headers={
        "Authorization": "Bearer invalid-token"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token(client):
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "non-existent-refresh-token"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_endpoints_in_openapi(client):
    response = await client.get("/openapi.json")
    paths = response.json()["paths"]
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/auth/me" in paths
