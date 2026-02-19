"""Auth API endpoints."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserInfo
from app.schemas.common import APIResponse
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory refresh token store (fallback when Redis is unavailable)
_refresh_tokens: dict[str, str] = {}  # refresh_token -> user_id

# Redis key prefix and TTL
_REFRESH_PREFIX = "refresh:"
_REFRESH_TTL = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


async def _store_refresh_token(token: str, user_id: str) -> None:
    """Store a refresh token mapping. Tries Redis first, falls back to in-memory."""
    try:
        from app.utils.redis_client import get_redis
        redis = await get_redis()
        await redis.set(f"{_REFRESH_PREFIX}{token}", user_id, ex=_REFRESH_TTL)
        # Also maintain a set of tokens per user for logout
        await redis.sadd(f"user_tokens:{user_id}", token)
        await redis.expire(f"user_tokens:{user_id}", _REFRESH_TTL)
        return
    except Exception:
        logger.debug("Redis unavailable for store_refresh_token, using in-memory fallback")
    _refresh_tokens[token] = user_id


async def _consume_refresh_token(token: str) -> str | None:
    """Get and delete a refresh token. Tries Redis first, falls back to in-memory."""
    try:
        from app.utils.redis_client import get_redis
        redis = await get_redis()
        key = f"{_REFRESH_PREFIX}{token}"
        user_id = await redis.get(key)
        if user_id:
            await redis.delete(key)
            # Remove from user's token set
            await redis.srem(f"user_tokens:{user_id}", token)
            return user_id
        return None
    except Exception:
        logger.debug("Redis unavailable for consume_refresh_token, using in-memory fallback")
    return _refresh_tokens.pop(token, None)


async def _revoke_all_user_tokens(user_id: str) -> None:
    """Delete all refresh tokens for a user. Tries Redis first, falls back to in-memory."""
    try:
        from app.utils.redis_client import get_redis
        redis = await get_redis()
        tokens = await redis.smembers(f"user_tokens:{user_id}")
        if tokens:
            keys = [f"{_REFRESH_PREFIX}{t}" for t in tokens]
            await redis.delete(*keys)
        await redis.delete(f"user_tokens:{user_id}")
        return
    except Exception:
        logger.debug("Redis unavailable for revoke_all_user_tokens, using in-memory fallback")
    to_remove = [k for k, v in _refresh_tokens.items() if v == user_id]
    for key in to_remove:
        _refresh_tokens.pop(key, None)


@router.post("/login", response_model=APIResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Get assigned client IDs
    client_ids = [str(a.client_id) for a in user.client_assignments]

    access_token = create_access_token(str(user.id), user.role.value, client_ids)
    refresh_token = create_refresh_token()
    await _store_refresh_token(refresh_token, str(user.id))

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    return APIResponse(
        status="success",
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ).model_dump(),
    )


@router.post("/refresh", response_model=APIResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    user_id = await _consume_refresh_token(body.refresh_token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    client_ids = [str(a.client_id) for a in user.client_assignments]
    new_access = create_access_token(str(user.id), user.role.value, client_ids)
    new_refresh = create_refresh_token()
    await _store_refresh_token(new_refresh, str(user.id))

    return APIResponse(
        status="success",
        data=TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
        ).model_dump(),
    )


@router.post("/logout", response_model=APIResponse)
async def logout(current_user: User = Depends(get_current_user)):
    # Invalidate all refresh tokens for this user
    await _revoke_all_user_tokens(str(current_user.id))

    return APIResponse(status="success", message="Logged out successfully")


@router.get("/me", response_model=APIResponse)
async def me(current_user: User = Depends(get_current_user)):
    return APIResponse(
        status="success",
        data=UserInfo.model_validate(current_user).model_dump(),
    )


@router.post("/oauth/{platform}/callback", response_model=APIResponse)
async def oauth_callback(
    platform: str,
    current_user: User = Depends(get_current_user),
):
    # Placeholder: will be implemented in STEP 16 (Meta) and STEP 17 (YouTube)
    return APIResponse(
        status="success",
        message=f"OAuth callback for {platform} - not yet implemented",
    )
