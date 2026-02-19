"""Shared response schemas."""
from typing import Any, Literal

from pydantic import BaseModel


class PaginationMeta(BaseModel):
    total: int
    page: int | None = None
    per_page: int | None = None
    cursor: str | None = None
    has_next: bool


class APIResponse(BaseModel):
    status: Literal["success", "error"]
    data: Any = None
    message: str | None = None
    pagination: PaginationMeta | None = None


class ErrorDetail(BaseModel):
    """RFC 7807 Problem Details."""
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None
