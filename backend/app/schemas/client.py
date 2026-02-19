"""Client request/response schemas."""
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.client import ClientStatus
from app.models.faq_guideline import FaqCategory
from app.models.platform_account import Platform


class ClientCreate(BaseModel):
    name: str = Field(max_length=200)
    industry: str | None = None
    manager_id: uuid.UUID
    contract_start: date | None = None
    contract_end: date | None = None


class ClientUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    industry: str | None = None
    contract_start: date | None = None
    contract_end: date | None = None


class ClientStatusUpdate(BaseModel):
    status: ClientStatus


class BrandGuidelinesUpdate(BaseModel):
    tone: str | None = None
    color_palette: list[str] | None = None
    forbidden_words: list[str] | None = None
    voice_profile: str | None = None


class ClientFilter(BaseModel):
    status: ClientStatus | None = None
    industry: str | None = None
    manager_id: uuid.UUID | None = None
    search: str | None = None
    page: int = 1
    per_page: int = 20


class ClientResponse(BaseModel):
    id: uuid.UUID
    name: str
    industry: str | None = None
    brand_guidelines: dict | None = None
    logo_url: str | None = None
    manager_id: uuid.UUID
    status: ClientStatus
    contract_start: date | None = None
    contract_end: date | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Platform Account ---

class PlatformAccountCreate(BaseModel):
    platform: Platform
    account_name: str = Field(max_length=200)
    access_token: str
    refresh_token: str | None = None


class PlatformAccountResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    platform: Platform
    account_name: str
    is_connected: bool
    token_expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- FAQ/Guideline ---

class FaqGuidelineCreate(BaseModel):
    category: FaqCategory
    title: str = Field(max_length=300)
    content: str
    tags: list[str] | None = None
    priority: int = 0


class FaqGuidelineUpdate(BaseModel):
    category: FaqCategory | None = None
    title: str | None = Field(None, max_length=300)
    content: str | None = None
    tags: list[str] | None = None
    priority: int | None = None
    is_active: bool | None = None


class FaqGuidelineResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    category: FaqCategory
    title: str
    content: str
    tags: list[str] | None = None
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
