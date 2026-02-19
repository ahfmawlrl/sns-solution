"""User request/response schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(max_length=100)
    role: UserRole
    client_ids: list[uuid.UUID] | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    avatar_url: str | None = None


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserActiveUpdate(BaseModel):
    is_active: bool


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserProfileUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    avatar_url: str | None = None


class UserFilter(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    search: str | None = None
    page: int = 1
    per_page: int = 20


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: UserRole
    is_active: bool
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
