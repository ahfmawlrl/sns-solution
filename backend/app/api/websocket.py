"""WebSocket endpoint with ConnectionManager, JWT auth, heartbeat, and Redis Pub/Sub."""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from app.services.auth_service import decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manage per-user WebSocket connections with optional Redis Pub/Sub for multi-instance."""

    def __init__(self):
        # user_id -> list of active websockets
        self.active_connections: dict[str, list[WebSocket]] = {}
        self._pubsub = None
        self._listener_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)
        logger.info("WS connected: user=%s (total=%d)", user_id, self._total())

    async def disconnect(self, websocket: WebSocket, user_id: str):
        conns = self.active_connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(user_id, None)
        logger.info("WS disconnected: user=%s (total=%d)", user_id, self._total())

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all local connections of a specific user."""
        for ws in self.active_connections.get(user_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("Failed to send WS message to user %s", user_id)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)

    def is_online(self, user_id: str) -> bool:
        return bool(self.active_connections.get(user_id))

    def online_users(self) -> list[str]:
        return list(self.active_connections.keys())

    def _total(self) -> int:
        return sum(len(v) for v in self.active_connections.values())

    # --- Redis Pub/Sub for cross-instance support ---

    async def start_redis_listener(self):
        """Start listening to Redis Pub/Sub for cross-instance messages."""
        try:
            from app.utils.redis_client import get_redis
            redis = await get_redis()
            self._pubsub = redis.pubsub()
            await self._pubsub.psubscribe("ws:user:*")
            self._listener_task = asyncio.create_task(self._redis_listener())
            logger.info("Redis Pub/Sub listener started for WebSocket")
        except Exception:
            logger.warning("Redis Pub/Sub unavailable, WebSocket limited to single instance")

    async def _redis_listener(self):
        """Background task to receive Redis Pub/Sub messages."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode()
                    user_id = channel.split(":")[-1]
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    try:
                        msg = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    # Only deliver to local connections
                    for ws in self.active_connections.get(user_id, []):
                        try:
                            await ws.send_json(msg)
                        except Exception:
                            pass
        except asyncio.CancelledError:
            logger.info("Redis Pub/Sub listener cancelled")
        except Exception:
            logger.warning("Redis Pub/Sub listener stopped")

    async def stop_redis_listener(self):
        """Stop the Redis Pub/Sub listener."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.punsubscribe("ws:user:*")
            await self._pubsub.close()
            self._pubsub = None

    async def publish_to_user(self, user_id: str, message: dict):
        """Send to user via Redis Pub/Sub (cross-instance) + local."""
        # Local delivery
        await self.send_to_user(user_id, message)
        # Redis Pub/Sub for other instances
        try:
            from app.utils.redis_client import get_redis
            redis = await get_redis()
            await redis.publish(f"ws:user:{user_id}", json.dumps(message))
        except Exception:
            pass


manager = ConnectionManager()


def verify_ws_token(token: str) -> dict | None:
    """Verify JWT token for WebSocket connection. Returns payload or None."""
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        return payload
    except JWTError:
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket endpoint with JWT authentication and 90s timeout.

    Client should send {"type": "ping"} every 30s to keep alive.
    Server responds with {"type": "pong"}.

    Events pushed to client:
        - notification: general notifications
        - crisis_alert: urgent crisis alerts
        - publish_result: publishing success/failure
        - approval_request: content status change requiring review
        - new_comment: new comment synced from platform
        - chat_stream: AI chat streaming chunks
    """
    # 1. JWT verification
    payload = verify_ws_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = payload["sub"]

    # 2. Accept & register
    await manager.connect(websocket, user_id)

    try:
        while True:
            # 90s timeout: if no message received, disconnect
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=90)
            except asyncio.TimeoutError:
                logger.info("WS timeout for user %s", user_id)
                await websocket.close(code=1000, reason="Timeout")
                break

            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WS error for user %s", user_id)
    finally:
        await manager.disconnect(websocket, user_id)
