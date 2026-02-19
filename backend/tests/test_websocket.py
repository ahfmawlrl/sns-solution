"""Tests for WebSocket endpoint and ConnectionManager."""
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from app.main import app
from app.api.websocket import ConnectionManager, verify_ws_token, manager
from app.services.auth_service import create_access_token
from app.models.user import UserRole

from tests.conftest import _create_test_user


# ── ConnectionManager unit tests ──


class FakeWebSocket:
    """Minimal fake WebSocket for unit-testing ConnectionManager."""

    def __init__(self):
        self.accepted = False
        self.sent: list[dict] = []
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, data: dict):
        self.sent.append(data)


@pytest.fixture
def conn_manager():
    """Return a fresh ConnectionManager for each test."""
    return ConnectionManager()


async def test_connect_and_disconnect(conn_manager):
    ws = FakeWebSocket()
    user_id = "user-1"

    await conn_manager.connect(ws, user_id)
    assert ws.accepted
    assert conn_manager.is_online(user_id)
    assert user_id in conn_manager.online_users()

    await conn_manager.disconnect(ws, user_id)
    assert not conn_manager.is_online(user_id)


async def test_send_to_user(conn_manager):
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()
    user_id = "user-2"

    await conn_manager.connect(ws1, user_id)
    await conn_manager.connect(ws2, user_id)

    msg = {"type": "notification", "title": "Test"}
    await conn_manager.send_to_user(user_id, msg)

    assert len(ws1.sent) == 1
    assert ws1.sent[0] == msg
    assert len(ws2.sent) == 1


async def test_send_to_offline_user(conn_manager):
    """Sending to an offline user should not raise."""
    await conn_manager.send_to_user("nonexistent", {"type": "test"})


async def test_broadcast(conn_manager):
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    await conn_manager.connect(ws1, "user-a")
    await conn_manager.connect(ws2, "user-b")

    msg = {"type": "crisis_alert", "severity": "high"}
    await conn_manager.broadcast(msg)

    assert len(ws1.sent) == 1
    assert len(ws2.sent) == 1


async def test_multiple_disconnect_same_user(conn_manager):
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()
    user_id = "user-multi"

    await conn_manager.connect(ws1, user_id)
    await conn_manager.connect(ws2, user_id)
    assert conn_manager.is_online(user_id)

    await conn_manager.disconnect(ws1, user_id)
    assert conn_manager.is_online(user_id)  # still online (ws2)

    await conn_manager.disconnect(ws2, user_id)
    assert not conn_manager.is_online(user_id)


# ── Token verification ──


def test_verify_ws_token_valid():
    token = create_access_token("user-123", "admin")
    payload = verify_ws_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"


def test_verify_ws_token_invalid():
    result = verify_ws_token("invalid.jwt.token")
    assert result is None


def test_verify_ws_token_empty():
    result = verify_ws_token("")
    assert result is None


# ── WebSocket endpoint integration (using Starlette TestClient) ──


def test_ws_connect_no_token():
    """WebSocket without token query param should fail."""
    client = TestClient(app)
    # Missing token should give an error
    with pytest.raises(Exception):
        with client.websocket_connect("/ws"):
            pass


def test_ws_connect_invalid_token():
    """WebSocket with invalid JWT should close with 4001."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=bad-token") as ws:
            ws.receive_json()


def test_ws_connect_valid_token_and_ping():
    """Valid JWT should connect successfully and respond to ping."""
    token = create_access_token(str(uuid.uuid4()), "operator")
    client = TestClient(app)
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.send_text(json.dumps({"type": "ping"}))
        resp = ws.receive_json()
        assert resp["type"] == "pong"


def test_ws_multiple_pings():
    """Multiple pings should all get pong responses."""
    token = create_access_token(str(uuid.uuid4()), "admin")
    client = TestClient(app)
    with client.websocket_connect(f"/ws?token={token}") as ws:
        for _ in range(3):
            ws.send_text(json.dumps({"type": "ping"}))
            resp = ws.receive_json()
            assert resp["type"] == "pong"


def test_ws_invalid_json_ignored():
    """Invalid JSON messages should be silently ignored."""
    token = create_access_token(str(uuid.uuid4()), "operator")
    client = TestClient(app)
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.send_text("not-json")
        # Send a valid ping to ensure connection still works
        ws.send_text(json.dumps({"type": "ping"}))
        resp = ws.receive_json()
        assert resp["type"] == "pong"
