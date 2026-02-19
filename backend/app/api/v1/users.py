"""Users API - 8 endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.user import (
    UserActiveUpdate,
    UserCreate,
    UserFilter,
    UserPasswordUpdate,
    UserProfileUpdate,
    UserResponse,
    UserRoleUpdate,
    UserUpdate,
)
from app.services import user_service
from app.services.auth_service import verify_password

router = APIRouter()


# GET /users — admin only
@router.get("", response_model=APIResponse)
async def list_users(
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _admin: User = require_role("admin"),
    db: AsyncSession = Depends(get_db),
):
    filters = UserFilter(role=role, is_active=is_active, search=search, page=page, per_page=per_page)
    users, total = await user_service.list_users(db, filters)
    return APIResponse(
        status="success",
        data=[UserResponse.model_validate(u).model_dump() for u in users],
        pagination=PaginationMeta(
            total=total, page=page, per_page=per_page,
            has_next=(page * per_page < total),
        ),
    )


# POST /users — admin only
@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    _admin: User = require_role("admin"),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.create_user(db, body)
    return APIResponse(
        status="success",
        data=UserResponse.model_validate(user).model_dump(),
        message="User created",
    )


# GET /users/{id} — admin, manager
@router.get("/{user_id}", response_model=APIResponse)
async def get_user(
    user_id: uuid.UUID,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return APIResponse(
        status="success",
        data=UserResponse.model_validate(user).model_dump(),
    )


# PUT /users/{id} — admin only
@router.put("/{user_id}", response_model=APIResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    _admin: User = require_role("admin"),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated = await user_service.update_user(db, user, name=body.name, avatar_url=body.avatar_url)
    return APIResponse(
        status="success",
        data=UserResponse.model_validate(updated).model_dump(),
    )


# PATCH /users/{id}/role — admin only
@router.patch("/{user_id}/role", response_model=APIResponse)
async def change_role(
    user_id: uuid.UUID,
    body: UserRoleUpdate,
    _admin: User = require_role("admin"),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = body.role
    return APIResponse(
        status="success",
        data=UserResponse.model_validate(user).model_dump(),
        message=f"Role changed to {body.role.value}",
    )


# PATCH /users/{id}/active — admin only
@router.patch("/{user_id}/active", response_model=APIResponse)
async def toggle_active(
    user_id: uuid.UUID,
    body: UserActiveUpdate,
    _admin: User = require_role("admin"),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = body.is_active
    return APIResponse(
        status="success",
        data=UserResponse.model_validate(user).model_dump(),
        message=f"User {'activated' if body.is_active else 'deactivated'}",
    )


# PUT /users/me/profile — authenticated
@router.put("/me/profile", response_model=APIResponse)
async def update_my_profile(
    body: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await user_service.update_user(db, current_user, name=body.name, avatar_url=body.avatar_url)
    return APIResponse(
        status="success",
        data=UserResponse.model_validate(updated).model_dump(),
    )


# PUT /users/me/password — authenticated
@router.put("/me/password", response_model=APIResponse)
async def change_my_password(
    body: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await user_service.change_password(db, current_user, body.new_password)
    return APIResponse(status="success", message="Password changed")
