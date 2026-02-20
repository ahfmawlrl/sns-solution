"""Encrypt a real Meta access token and store it in the DB platform_account record.

Usage (from backend/ directory):
    INSTAGRAM_ACCESS_TOKEN=EAACs... python scripts/register_instagram_token.py --account-id <uuid>

The script:
  1. Reads the token from INSTAGRAM_ACCESS_TOKEN env var (or --token CLI arg).
  2. Calls Meta Graph API /me to validate the token.
  3. Encrypts the token with AES-256-GCM using settings.ENCRYPTION_KEY.
  4. Updates the platform_account row (access_token, is_connected=True).

Prerequisites:
    - DB contains the platform_account record (run seed_test_data.py first).
    - ENCRYPTION_KEY is set in .env.
    - META_APP_ID / META_APP_SECRET are set in .env (optional — only needed for token exchange).
"""
import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path

# Windows: asyncpg requires SelectorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base  # noqa: F401
from app.models.platform_account import PlatformAccount
from app.utils.encryption import TokenEncryptor


async def validate_token(token: str) -> dict:
    """Call Meta Graph API /me and return the response dict."""
    async with httpx.AsyncClient(
        base_url="https://graph.facebook.com/v19.0", timeout=15.0
    ) as client:
        resp = await client.get("/me", params={"access_token": token, "fields": "id,name,username"})
        resp.raise_for_status()
        return resp.json()


async def register(session: AsyncSession, account_id: uuid.UUID, token: str) -> None:
    # ── 1. Validate token with Meta Graph API ────────────────────────────────
    print("Validating token with Meta Graph API…")
    try:
        me = await validate_token(token)
    except httpx.HTTPStatusError as exc:
        print(f"ERROR: Meta API returned {exc.response.status_code}: {exc.response.text}")
        return
    except Exception as exc:
        print(f"ERROR: Could not reach Meta API — {exc}")
        return

    if "id" not in me:
        print(f"ERROR: Unexpected response from Meta API: {me}")
        return

    print(f"Token valid. me={me}")

    # ── 2. Encrypt token ─────────────────────────────────────────────────────
    if not settings.ENCRYPTION_KEY:
        print("ERROR: ENCRYPTION_KEY is not set in .env. Cannot encrypt token.")
        return

    encryptor = TokenEncryptor(settings.ENCRYPTION_KEY)
    encrypted_token = encryptor.encrypt(token)

    # ── 3. Update DB record ──────────────────────────────────────────────────
    account: PlatformAccount | None = await session.get(PlatformAccount, account_id)
    if account is None:
        print(f"ERROR: PlatformAccount {account_id} not found. Run seed_test_data.py first.")
        return

    account.access_token = encrypted_token
    account.is_connected = True
    await session.commit()

    print()
    print("─" * 60)
    print("Token registered successfully!")
    print(f"  account_id   = {account.id}")
    print(f"  account_name = {account.account_name}")
    print(f"  is_connected = {account.is_connected}")
    print(f"  meta_id      = {me.get('id')}")
    print(f"  meta_name    = {me.get('name')}")
    print()
    print("Next step:")
    print("  POST /api/v1/settings/platform-connections/test")
    print(f"  body: {{\"platform_account_id\": \"{account.id}\"}}")
    print("─" * 60)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Register an Instagram access token.")
    parser.add_argument(
        "--account-id",
        required=True,
        help="UUID of the PlatformAccount row (output from seed_test_data.py)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Meta access token (overrides INSTAGRAM_ACCESS_TOKEN env var)",
    )
    args = parser.parse_args()

    token = args.token or os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    if not token:
        print(
            "ERROR: Provide the token via INSTAGRAM_ACCESS_TOKEN env var "
            "or --token CLI argument."
        )
        sys.exit(1)

    try:
        account_id = uuid.UUID(args.account_id)
    except ValueError:
        print(f"ERROR: Invalid UUID: {args.account_id!r}")
        sys.exit(1)

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await register(session, account_id, token)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
