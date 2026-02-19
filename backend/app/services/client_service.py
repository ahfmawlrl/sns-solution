"""Client business logic."""
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.faq_guideline import FaqGuideline
from app.models.platform_account import PlatformAccount
from app.schemas.client import (
    ClientCreate,
    ClientFilter,
    FaqGuidelineCreate,
    FaqGuidelineUpdate,
    PlatformAccountCreate,
)


async def create_client(db: AsyncSession, data: ClientCreate) -> Client:
    client = Client(
        name=data.name,
        industry=data.industry,
        manager_id=data.manager_id,
        contract_start=data.contract_start,
        contract_end=data.contract_end,
    )
    db.add(client)
    await db.flush()
    return client


async def get_client(db: AsyncSession, client_id: uuid.UUID) -> Client | None:
    return await db.get(Client, client_id)


async def list_clients(
    db: AsyncSession, filters: ClientFilter
) -> tuple[list[Client], int]:
    query = select(Client)

    if filters.status is not None:
        query = query.where(Client.status == filters.status)
    if filters.industry:
        query = query.where(Client.industry == filters.industry)
    if filters.manager_id:
        query = query.where(Client.manager_id == filters.manager_id)
    if filters.search:
        search = f"%{filters.search}%"
        query = query.where(or_(Client.name.ilike(search), Client.industry.ilike(search)))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (filters.page - 1) * filters.per_page
    query = query.order_by(Client.created_at.desc()).offset(offset).limit(filters.per_page)
    result = await db.execute(query)
    clients = list(result.scalars().all())

    return clients, total


async def update_client(db: AsyncSession, client: Client, **kwargs) -> Client:
    for key, value in kwargs.items():
        if value is not None:
            setattr(client, key, value)
    return client


# --- Platform Accounts ---

async def add_platform_account(
    db: AsyncSession, client_id: uuid.UUID, data: PlatformAccountCreate
) -> PlatformAccount:
    account = PlatformAccount(
        client_id=client_id,
        platform=data.platform,
        account_name=data.account_name,
        access_token=data.access_token,
        refresh_token=data.refresh_token,
    )
    db.add(account)
    await db.flush()
    return account


async def list_platform_accounts(
    db: AsyncSession, client_id: uuid.UUID
) -> list[PlatformAccount]:
    result = await db.execute(
        select(PlatformAccount).where(PlatformAccount.client_id == client_id)
    )
    return list(result.scalars().all())


async def delete_platform_account(db: AsyncSession, account_id: uuid.UUID) -> bool:
    account = await db.get(PlatformAccount, account_id)
    if not account:
        return False
    await db.delete(account)
    return True


# --- FAQ/Guidelines ---

async def create_faq(
    db: AsyncSession, client_id: uuid.UUID, data: FaqGuidelineCreate
) -> FaqGuideline:
    faq = FaqGuideline(
        client_id=client_id,
        category=data.category,
        title=data.title,
        content=data.content,
        tags=data.tags,
        priority=data.priority,
    )
    db.add(faq)
    await db.flush()
    return faq


async def list_faqs(db: AsyncSession, client_id: uuid.UUID) -> list[FaqGuideline]:
    result = await db.execute(
        select(FaqGuideline)
        .where(FaqGuideline.client_id == client_id)
        .order_by(FaqGuideline.priority.desc(), FaqGuideline.created_at.desc())
    )
    return list(result.scalars().all())


async def update_faq(
    db: AsyncSession, faq: FaqGuideline, data: FaqGuidelineUpdate
) -> FaqGuideline:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(faq, key, value)
    return faq


async def delete_faq(db: AsyncSession, faq_id: uuid.UUID) -> bool:
    faq = await db.get(FaqGuideline, faq_id)
    if not faq:
        return False
    await db.delete(faq)
    return True
