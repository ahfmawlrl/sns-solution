"""Seed test client + Instagram platform account for real API integration testing.

Usage (from backend/ directory):
    python scripts/seed_test_data.py

Prerequisites:
    - DB is running and migrated (alembic upgrade head)
    - admin@sns.com user exists (created by the auth seed or first run)
    - ENCRYPTION_KEY is set in .env
"""
import asyncio
import sys
from pathlib import Path

# Windows: asyncpg requires SelectorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Allow imports from backend/app/
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base  # noqa: F401 — ensures all models are registered
from app.models.client import Client, ClientStatus
from app.models.platform_account import Platform, PlatformAccount
from app.models.user import User
from app.utils.encryption import TokenEncryptor

# Placeholder token stored before a real token is registered via register_instagram_token.py
_PLACEHOLDER_TOKEN = "PLACEHOLDER_REPLACE_WITH_REAL_TOKEN"


async def seed(session: AsyncSession) -> None:
    # ── 1. Find admin user ──────────────────────────────────────────────────
    result = await session.execute(select(User).where(User.email == "admin@sns.com"))
    admin: User | None = result.scalars().first()
    if admin is None:
        print(
            "ERROR: admin@sns.com not found. "
            "Run the server once (it seeds the admin on startup) or create the user manually."
        )
        return

    # ── 2. Create test client (idempotent) ──────────────────────────────────
    result = await session.execute(select(Client).where(Client.name == "테스트 브랜드"))
    client: Client | None = result.scalars().first()

    if client is None:
        client = Client(
            name="테스트 브랜드",
            industry="테크",
            manager_id=admin.id,
            status=ClientStatus.ACTIVE,
        )
        session.add(client)
        await session.flush()  # get client.id before inserting platform_account
        print(f"Created client: 테스트 브랜드 (id={client.id})")
    else:
        print(f"Client already exists: 테스트 브랜드 (id={client.id})")

    # ── 3. Create Instagram platform account (idempotent) ───────────────────
    result = await session.execute(
        select(PlatformAccount).where(
            PlatformAccount.client_id == client.id,
            PlatformAccount.platform == Platform.INSTAGRAM,
        )
    )
    account: PlatformAccount | None = result.scalars().first()

    if account is None:
        # Encrypt the placeholder so the column is never plaintext
        if settings.ENCRYPTION_KEY:
            encryptor = TokenEncryptor(settings.ENCRYPTION_KEY)
            encrypted_placeholder = encryptor.encrypt(_PLACEHOLDER_TOKEN)
        else:
            encrypted_placeholder = _PLACEHOLDER_TOKEN
            print(
                "WARNING: ENCRYPTION_KEY is not set in .env — "
                "storing plaintext placeholder. Set the key before registering a real token."
            )

        account = PlatformAccount(
            client_id=client.id,
            platform=Platform.INSTAGRAM,
            account_name="테스트 인스타그램",
            access_token=encrypted_placeholder,
            is_connected=False,
        )
        session.add(account)
        await session.flush()
        print(f"Created platform account: 테스트 인스타그램 (id={account.id})")
    else:
        print(f"Platform account already exists: {account.account_name} (id={account.id})")

    await session.commit()

    print()
    print("─" * 60)
    print("Seeded successfully!")
    print(f"  client_id  = {client.id}")
    print(f"  account_id = {account.id}")
    print()
    print("Next step:")
    print(
        f"  INSTAGRAM_ACCESS_TOKEN=<your_token> "
        f"python scripts/register_instagram_token.py --account-id {account.id}"
    )
    print("─" * 60)


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
