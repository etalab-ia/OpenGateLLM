from collections.abc import AsyncGenerator
from types import SimpleNamespace

import asyncpg
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.app import create_app
from api.dependencies import get_postgres_session
from api.sql.models import Base
from api.tests.integration import factories

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:changeme@localhost:5432/test_db"


@pytest.fixture
def test_configuration():
    return SimpleNamespace(
        settings=SimpleNamespace(
            app_title="test",
            swagger_summary=None,
            swagger_version="0.0.0",
            swagger_description=None,
            swagger_terms_of_service=None,
            swagger_contact=None,
            swagger_license_info=None,
            swagger_openapi_tags=[],
            swagger_docs_url=None,
            swagger_redoc_url=None,
            session_secret_key="test-secret-key",
            disabled_routers=[],
            hidden_routers=[],
            monitoring_prometheus_enabled=False,
        ),
        dependencies=SimpleNamespace(sentry=None),
    )


@pytest_asyncio.fixture(scope="session")
async def test_engine():
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
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def db_session(test_session_factory) -> AsyncGenerator[AsyncSession]:
    async with test_session_factory() as session:
        all_sql_factories = factories.BaseSQLFactory.__subclasses__()
        session.expire_on_commit = False
        try:
            async with session.begin_nested():
                for factory in all_sql_factories:
                    factory._meta.sqlalchemy_session = session
                yield session
        finally:
            if session.in_transaction():
                await session.rollback()
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def client(db_session, test_configuration) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(test_configuration, skip_lifespan=True)

    async def override_get_postgres_session():
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
