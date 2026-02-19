"""Auth request/response schemas."""
from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    is_active: bool
    avatar_url: str | None = None

    model_config = {"from_attributes": True}
