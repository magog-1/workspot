"""Pytest fixtures for the WorkSpot test suite.

Integration tests (marked with ``@pytest.mark.integration``) require a real
PostgreSQL instance because the models rely on Postgres-specific column types
(``ARRAY``, ``UUID``). The connection string is taken from ``DATABASE_URL`` and
defaults to the value used in CI.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

# Ensure required env vars exist before importing the app — Pydantic Settings
# validation runs at import time.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:test@localhost:5433/workspot_test",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-must-be-at-least-32-chars")


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ["DATABASE_URL"]


@pytest.fixture
def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


# ---------------------------------------------------------------------------
# Integration fixtures (Postgres-only)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def test_engine(database_url: str):
    """Create the schema once per test session against a real Postgres."""
    from sqlalchemy.ext.asyncio import create_async_engine

    # Importing models registers them on Base.metadata.
    import auth.models  # noqa: F401
    import bookings.models  # noqa: F401
    import spaces.models  # noqa: F401
    from database import Base

    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(test_engine):
    """HTTP client wired to the FastAPI app with the test database."""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from database import get_db
    from main import app

    async_session = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
