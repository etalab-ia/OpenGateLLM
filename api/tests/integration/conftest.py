from collections.abc import AsyncGenerator
from contextvars import ContextVar

import asyncpg
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
import redis.asyncio as redis
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from api.app import create_app
from api.dependencies import get_postgres_session, get_redis_client
from api.helpers.models import ModelRegistry
from api.schemas.core.configuration import Configuration, Dependencies, Settings
from api.sql.models import Base
from api.tests.integration import factories
from api.utils.dependencies import get_model_registry
from api.utils.dependencies import get_postgres_session as get_postgres_session_utils
from api.utils.dependencies import get_redis_client as get_redis_client_utils

TEST_POSTGRES_URL = "postgresql+asyncpg://postgres:changeme@localhost:5432/test_db"
TEST_REDIS_URL = "redis://:changeme@localhost:6379/1"
_current_db_session: ContextVar[AsyncSession | None] = ContextVar("_current_db_session", default=None)


@pytest.fixture(scope="session")
def test_configuration():
    configuration = Configuration.model_construct(
        settings=Settings.model_construct(
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
            disabled_routers=[],
            hidden_routers=[],
            monitoring_prometheus_enabled=False,
        ),
        dependencies=Dependencies.model_construct(sentry=None),
    )
    return configuration


@pytest_asyncio.fixture(scope="session")
async def test_redis_pool(test_configuration):
    pool = redis.ConnectionPool.from_url(url=TEST_REDIS_URL)
    pool.url = TEST_REDIS_URL
    client = redis.Redis(connection_pool=pool)
    if not await client.ping():
        raise RuntimeError("Redis database is not reachable.")
    await client.aclose()

    yield pool

    await pool.aclose()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _reset_redis_between_tests(test_redis_pool):
    client = redis.Redis(connection_pool=test_redis_pool)
    try:
        await client.flushdb()
        yield
        await client.flushdb()
    finally:
        await client.aclose()


@pytest_asyncio.fixture(scope="session")
async def test_postgres_engine():
    conn = await asyncpg.connect("postgresql://postgres:changeme@localhost:5432/postgres")
    try:
        await conn.execute("CREATE DATABASE test_db")
    except asyncpg.exceptions.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()

    engine = create_async_engine(url=TEST_POSTGRES_URL, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


def _all_sql_factories():
    result = []
    stack = list(factories.sql.BaseSQLFactory.__subclasses__())
    while stack:
        cls = stack.pop()
        result.append(cls)
        stack.extend(cls.__subclasses__())
    return result


def pytest_addoption(parser):
    parser.addoption(
        "--commit-db",
        action="store_true",
        default=False,
        help="Commit DB changes after each test (for debugging with psql).",
    )


@pytest_asyncio.fixture(scope="function")
async def db_session(test_postgres_engine, request) -> AsyncGenerator[AsyncSession]:
    async with test_postgres_engine.connect() as connection:
        postgres_outer_transaction = await connection.begin()

        session = AsyncSession(bind=connection, expire_on_commit=False)
        await session.begin_nested()

        all_sql_factories = _all_sql_factories()
        for factory in all_sql_factories:
            factory._meta.sqlalchemy_session = session

        @event.listens_for(session.sync_session, "after_transaction_end")
        def restart_savepoint(sess, trans):
            if trans.nested and not trans._parent.nested:
                sess.begin_nested()

        token = _current_db_session.set(session)
        try:
            yield session
        finally:
            _current_db_session.reset(token)
            event.remove(session.sync_session, "after_transaction_end", restart_savepoint)
            for factory in all_sql_factories:
                factory._meta.sqlalchemy_session = None
            await session.close()
            if request.config.getoption("--commit-db"):
                await postgres_outer_transaction.commit()
            else:
                await postgres_outer_transaction.rollback()


@pytest_asyncio.fixture(scope="function")
async def redis_client(test_redis_pool) -> AsyncGenerator[redis.Redis]:
    client = redis.Redis(connection_pool=test_redis_pool)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture(scope="session")
def model_registry():
    return ModelRegistry(
        app_title="test",
        queuing_enabled=False,
        max_priority=0,
        max_retries=0,
        retry_countdown=0,
    )


@pytest_asyncio.fixture(scope="session")
async def app(model_registry, test_configuration, test_redis_pool):
    app = create_app(test_configuration, skip_lifespan=True)

    async def override_get_postgres_session():
        session = _current_db_session.get()
        try:
            yield session
            if session.in_transaction():
                await session.flush()
        except Exception:
            if session.in_transaction():
                await session.rollback()
            raise

    async def override_get_redis_client():
        client = redis.Redis(connection_pool=test_redis_pool)
        try:
            yield client
        finally:
            await client.aclose()

    app.dependency_overrides[get_postgres_session] = override_get_postgres_session
    app.dependency_overrides[get_postgres_session_utils] = override_get_postgres_session  # @TODO: remove after legacy migration
    app.dependency_overrides[get_redis_client] = override_get_redis_client
    app.dependency_overrides[get_redis_client_utils] = override_get_redis_client  # @TODO: remove after legacy migration
    app.dependency_overrides[get_model_registry] = lambda: model_registry

    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session")
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
