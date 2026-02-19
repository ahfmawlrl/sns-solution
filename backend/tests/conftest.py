"""Shared test fixtures with in-memory SQLite."""
import json
import sqlite3
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.models.base import Base
from app.models.user import User, UserRole
from app.main import app
from app.dependencies import get_db
from app.services.auth_service import create_access_token, hash_password

# --- SQLite compatibility: compile PostgreSQL types for SQLite ---

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "JSON"


# Register Python list adapter for sqlite3 so ARRAY columns can be inserted
sqlite3.register_adapter(list, lambda val: json.dumps(val))
sqlite3.register_converter("JSON", lambda val: json.loads(val))

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(test_engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db():
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    async with test_session_factory() as session:
        yield session


async def _create_test_user(
    db: AsyncSession, role: UserRole = UserRole.ADMIN, email: str | None = None,
) -> tuple[User, str]:
    """Create a test user and return (user, access_token)."""
    user = User(
        id=uuid.uuid4(),
        email=email or f"{role.value}_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("testpass123"),
        name=f"Test {role.value.title()}",
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(str(user.id), role.value)
    return user, token


@pytest.fixture
async def admin_auth(db_session: AsyncSession) -> tuple[User, dict]:
    """Return (admin_user, auth_headers)."""
    user, token = await _create_test_user(db_session, UserRole.ADMIN)
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def manager_auth(db_session: AsyncSession) -> tuple[User, dict]:
    user, token = await _create_test_user(db_session, UserRole.MANAGER)
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def operator_auth(db_session: AsyncSession) -> tuple[User, dict]:
    user, token = await _create_test_user(db_session, UserRole.OPERATOR)
    return user, {"Authorization": f"Bearer {token}"}
