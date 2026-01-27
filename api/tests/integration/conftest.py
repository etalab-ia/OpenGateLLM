from collections.abc import AsyncGenerator

import asyncpg
from httpx import ASGITransport, AsyncClient
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.dependencies import get_postgres_session
from api.main import app
from api.sql.models import Base
from api.tests.integration import factories

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:changeme@localhost:5432/test_db"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    conn = await asyncpg.connect("postgresql://postgres:changeme@localhost:5432/postgres")
    try:
        await conn.execute("CREATE DATABASE test_db")
    except asyncpg.exceptions.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    """Create a session factory for tests."""
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def db_session(test_session_factory) -> AsyncGenerator[AsyncSession]:
    """Provide a transactional scope for each test."""
    async with test_session_factory() as session:
        all_sql_factories = factories.BaseSQLFactory.__subclasses__()
        session.expire_on_commit = False
        try:
            async with session.begin_nested():
                for factory in all_sql_factories:
                    factory._meta.sqlalchemy_session = session
                yield session
                await session.rollback()
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden database dependency."""

    async def override_get_postgres_session():
        """Override the database session dependency."""
        try:
            yield db_session
            if db_session.in_transaction():
                await db_session.flush()
        except Exception:
            if db_session.in_transaction():
                await db_session.rollback()
            raise

    app.dependency_overrides[get_postgres_session] = override_get_postgres_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
