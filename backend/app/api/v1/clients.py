"""Clients API - 13 endpoints."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.dependencies import get_current_user, get_db, require_role
from app.models.client import Client, ClientStatus
from app.models.user import User
from app.schemas.client import (
    BrandGuidelinesUpdate,
    ClientCreate,
    ClientFilter,
    ClientResponse,
    ClientStatusUpdate,
    ClientUpdate,
    FaqGuidelineCreate,
    FaqGuidelineResponse,
    FaqGuidelineUpdate,
    PlatformAccountCreate,
    PlatformAccountResponse,
)
from app.schemas.common import APIResponse, PaginationMeta
from app.services import client_service

router = APIRouter()


# GET /clients
@router.get("", response_model=APIResponse)
async def list_clients(
    status_filter: ClientStatus | None = Query(None, alias="status"),
    industry: str | None = None,
    manager_id: uuid.UUID | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = ClientFilter(
        status=status_filter, industry=industry, manager_id=manager_id,
        search=search, page=page, per_page=per_page,
    )
    clients, total = await client_service.list_clients(db, filters)
    return APIResponse(
        status="success",
        data=[ClientResponse.model_validate(c).model_dump() for c in clients],
        pagination=PaginationMeta(
            total=total, page=page, per_page=per_page,
            has_next=(page * per_page < total),
        ),
    )


# POST /clients — admin, manager
@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.create_client(db, body)
    return APIResponse(
        status="success",
        data=ClientResponse.model_validate(client).model_dump(),
        message="Client created",
    )


# GET /clients/{id}
@router.get("/{client_id}", response_model=APIResponse)
async def get_client(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return APIResponse(
        status="success",
        data=ClientResponse.model_validate(client).model_dump(),
    )


# PUT /clients/{id} — admin, manager
@router.put("/{client_id}", response_model=APIResponse)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    updated = await client_service.update_client(
        db, client,
        name=body.name, industry=body.industry,
        contract_start=body.contract_start, contract_end=body.contract_end,
    )
    return APIResponse(
        status="success",
        data=ClientResponse.model_validate(updated).model_dump(),
    )


# PATCH /clients/{id}/status — admin, manager
@router.patch("/{client_id}/status", response_model=APIResponse)
async def change_status(
    client_id: uuid.UUID,
    body: ClientStatusUpdate,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.status = body.status
    return APIResponse(
        status="success",
        data=ClientResponse.model_validate(client).model_dump(),
        message=f"Status changed to {body.status.value}",
    )


# PUT /clients/{id}/brand-guidelines — admin, manager
@router.put("/{client_id}/brand-guidelines", response_model=APIResponse)
async def update_brand_guidelines(
    client_id: uuid.UUID,
    body: BrandGuidelinesUpdate,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.brand_guidelines = body.model_dump(exclude_unset=True)
    return APIResponse(
        status="success",
        data=ClientResponse.model_validate(client).model_dump(),
        message="Brand guidelines updated",
    )


# --- Platform Accounts ---

# GET /clients/{id}/accounts
@router.get("/{client_id}/accounts", response_model=APIResponse)
async def list_accounts(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accounts = await client_service.list_platform_accounts(db, client_id)
    return APIResponse(
        status="success",
        data=[PlatformAccountResponse.model_validate(a).model_dump() for a in accounts],
    )


# POST /clients/{id}/accounts — admin, manager
@router.post("/{client_id}/accounts", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def add_account(
    client_id: uuid.UUID,
    body: PlatformAccountCreate,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    account = await client_service.add_platform_account(db, client_id, body)
    return APIResponse(
        status="success",
        data=PlatformAccountResponse.model_validate(account).model_dump(),
        message="Platform account linked",
    )


# DELETE /clients/{id}/accounts/{accountId} — admin, manager
@router.delete("/{client_id}/accounts/{account_id}", response_model=APIResponse)
async def remove_account(
    client_id: uuid.UUID,
    account_id: uuid.UUID,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    deleted = await client_service.delete_platform_account(db, account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Platform account not found")
    return APIResponse(status="success", message="Platform account unlinked")


# --- FAQ/Guidelines ---

# GET /clients/{id}/faq-guidelines
@router.get("/{client_id}/faq-guidelines", response_model=APIResponse)
async def list_faqs(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    faqs = await client_service.list_faqs(db, client_id)
    return APIResponse(
        status="success",
        data=[FaqGuidelineResponse.model_validate(f).model_dump() for f in faqs],
    )


# POST /clients/{id}/faq-guidelines — admin, manager, operator
@router.post("/{client_id}/faq-guidelines", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_faq(
    client_id: uuid.UUID,
    body: FaqGuidelineCreate,
    _caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    faq = await client_service.create_faq(db, client_id, body)

    # Auto-index FAQ into vector store for RAG retrieval
    try:
        from app.integrations.ai.rag import RAGPipeline
        rag = RAGPipeline()
        await rag.index_faq(db, faq)
    except Exception:
        logger.warning("Failed to auto-index FAQ %s", faq.id)

    return APIResponse(
        status="success",
        data=FaqGuidelineResponse.model_validate(faq).model_dump(),
        message="FAQ/Guideline created",
    )


# PUT /clients/{id}/faq-guidelines/{faqId} — admin, manager, operator
@router.put("/{client_id}/faq-guidelines/{faq_id}", response_model=APIResponse)
async def update_faq(
    client_id: uuid.UUID,
    faq_id: uuid.UUID,
    body: FaqGuidelineUpdate,
    _caller: User = require_role("admin", "manager", "operator"),
    db: AsyncSession = Depends(get_db),
):
    from app.models.faq_guideline import FaqGuideline
    faq = await db.get(FaqGuideline, faq_id)
    if not faq or faq.client_id != client_id:
        raise HTTPException(status_code=404, detail="FAQ/Guideline not found")
    updated = await client_service.update_faq(db, faq, body)

    # Re-index updated FAQ into vector store (best-effort, non-blocking)
    try:
        from app.integrations.ai.rag import RAGPipeline
        rag = RAGPipeline()
        await rag.index_faq(db, updated)
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        logger.warning("Failed to re-index FAQ %s", faq_id)

    # Ensure the object is in a valid state for serialization
    try:
        await db.refresh(updated)
    except Exception:
        updated = await db.get(FaqGuideline, faq_id)

    return APIResponse(
        status="success",
        data=FaqGuidelineResponse.model_validate(updated).model_dump(),
    )


# DELETE /clients/{id}/faq-guidelines/{faqId} — admin, manager
@router.delete("/{client_id}/faq-guidelines/{faq_id}", response_model=APIResponse)
async def delete_faq(
    client_id: uuid.UUID,
    faq_id: uuid.UUID,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    deleted = await client_service.delete_faq(db, faq_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="FAQ/Guideline not found")
    return APIResponse(status="success", message="FAQ/Guideline deleted")
