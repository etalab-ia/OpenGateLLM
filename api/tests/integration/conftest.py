import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Iterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager, contextmanager
import os

import asyncpg
from fastapi import BackgroundTasks
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
import redis.asyncio as redis
from sqlalchemy import event, make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine

from api.app import create_app
from api.dependencies import get_autocommit_postgres_session, get_postgres_session, get_redis_client
from api.domain.router import RouterRateLimiter
from api.infrastructure.configuration import Configuration, Dependencies, Settings, get_configuration
from api.infrastructure.context import GlobalContext, global_context
from api.infrastructure.postgres import PostgresUsageRepository
from api.infrastructure.postgres.models import Base
from api.infrastructure.redis import RedisRouterRateLimiter
from api.tests.helpers import TEST_AUTH_SECRET_KEY
from api.tests.integration import factories


def _test_postgres_url() -> str:
    url = make_url(os.getenv("TEST_POSTGRES_URL", "postgresql+asyncpg://postgres:changeme@localhost:5432/test_db"))
    xdist_worker = os.getenv("PYTEST_XDIST_WORKER")
    if xdist_worker and url.database:
        url = url.set(database=f"{url.database}_{xdist_worker}")
    return url.render_as_string(hide_password=False)


def _test_redis_url() -> str:
    url = os.getenv("TEST_REDIS_URL", "redis://:changeme@localhost:6379/1")
    xdist_worker = os.getenv("PYTEST_XDIST_WORKER")
    if not xdist_worker:
        return url
    base_url, db = url.rsplit("/", 1)
    xdist_worker_index = int(xdist_worker.removeprefix("gw"))
    return f"{base_url}/{int(db) + xdist_worker_index}"


TEST_POSTGRES_URL = _test_postgres_url()
TEST_REDIS_URL = _test_redis_url()

_shared_test_session: "SharedTestSession | None" = None


@pytest.fixture(scope="session")
def test_configuration():
    return Configuration.model_construct(settings=_test_settings(), dependencies=Dependencies.model_construct(sentry=None))


def _test_settings() -> Settings:
    test_config_file = os.getenv("TEST_CONFIG_FILE")
    if test_config_file:
        settings = Configuration(config_file=test_config_file).settings
        return settings.model_copy(update={"auth_secret_key": TEST_AUTH_SECRET_KEY, "monitoring_prometheus_enabled": False})

    return Settings.model_construct(
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
        auth_secret_key=TEST_AUTH_SECRET_KEY,
        auth_key_max_expiration_days=None,
    )


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


@pytest.fixture
def router_rate_limiter(test_redis_pool, test_configuration) -> RouterRateLimiter:
    return RedisRouterRateLimiter(
        background_tasks=BackgroundTasks(),
        redis_pool=test_redis_pool,
        strategy=test_configuration.settings.rate_limiting_strategy,
        cached_tokens_discount=test_configuration.settings.rate_limiting_cached_tokens_discount,
    )


@pytest_asyncio.fixture(scope="session")
async def test_postgres_engine():
    test_postgres_url = make_url(TEST_POSTGRES_URL)
    if not test_postgres_url.database:
        raise ValueError(f"TEST_POSTGRES_URL must name a database: {test_postgres_url}")
    maintenance_url = test_postgres_url.set(drivername="postgresql", database="postgres", query={})
    conn = await asyncpg.connect(maintenance_url.render_as_string(hide_password=False))
    try:
        await conn.execute(f'CREATE DATABASE "{test_postgres_url.database}"')
    except asyncpg.exceptions.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()

    engine = create_async_engine(url=test_postgres_url)

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


@contextmanager
def override_global_context(**overrides):
    unknown = sorted(set(overrides) - set(GlobalContext.model_fields))
    if unknown:
        raise AttributeError(f"GlobalContext has no field {unknown}: the override would silently do nothing.")

    previous = {key: getattr(global_context, key) for key in overrides}
    for key, value in overrides.items():
        setattr(global_context, key, value)
    try:
        yield
    finally:
        for key, value in previous.items():
            setattr(global_context, key, value)


@contextmanager
def bind_sql_factories(session):
    all_factories = _all_sql_factories()
    for factory in all_factories:
        factory._meta.sqlalchemy_session = session
    try:
        yield
    finally:
        for factory in all_factories:
            factory._meta.sqlalchemy_session = None


def pytest_addoption(parser):
    parser.addoption(
        "--commit-db",
        action="store_true",
        default=False,
        help="Commit DB changes after each test (for debugging with psql).",
    )


class SharedTestSession:
    """In production, HTTP requests and usage saves each take a session from the pool. Here they share the test session,
    which cannot run two operations at once. A usage save runs in its own asyncio task, which outlives the request, so
    they take turns: a usage save waits for the HTTP requests using the session, an HTTP request waits for the usage
    saves. Counters rather than a lock: one HTTP request takes the session through two dependencies."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._turns = asyncio.Condition()
        self._http_requests_using_session = 0
        self._usage_saves_using_session = 0

    @asynccontextmanager
    async def session_for_http_request(self) -> AsyncIterator[AsyncSession]:
        async with self._turns:
            await self._turns.wait_for(lambda: self._usage_saves_using_session == 0)
            self._http_requests_using_session += 1
        try:
            yield self.session
        finally:
            async with self._turns:
                self._http_requests_using_session -= 1
                self._turns.notify_all()

    @asynccontextmanager
    async def session_for_usage_save(self) -> AsyncIterator[AsyncSession]:
        async with self._turns:
            await self._turns.wait_for(lambda: self._http_requests_using_session == 0)
            self._usage_saves_using_session += 1
        try:
            yield self.session
        finally:
            async with self._turns:
                self._usage_saves_using_session -= 1
                self._turns.notify_all()


def _shared_session_for_usage_save() -> AbstractAsyncContextManager[AsyncSession]:
    return _shared_test_session.session_for_usage_save()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_postgres_engine, request) -> AsyncGenerator[AsyncSession]:
    async with test_postgres_engine.connect() as connection:
        test_transaction = await connection.begin()
        async with _nested_session(connection) as session:
            with _connect_the_app_and_the_factories_to(session):
                yield session
                await PostgresUsageRepository.wait_for_pending_saves(timeout=5)
        if request.config.getoption("--commit-db"):
            await test_transaction.commit()
        else:
            await test_transaction.rollback()


@asynccontextmanager
async def _nested_session(connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    """The code under test commits: each commit only releases a savepoint, and a new one opens right after, so the
    test transaction stays open until the teardown rolls it back."""
    session = AsyncSession(bind=connection, expire_on_commit=False)
    await session.begin_nested()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        event.remove(session.sync_session, "after_transaction_end", restart_savepoint)
        await session.close()


@contextmanager
def _connect_the_app_and_the_factories_to(session: AsyncSession) -> Iterator[None]:
    global _shared_test_session
    _shared_test_session = SharedTestSession(session)
    try:
        with bind_sql_factories(session), override_global_context(autocommit_postgres_session_factory=_shared_session_for_usage_save):
            yield
    finally:
        _shared_test_session = None


@pytest_asyncio.fixture(scope="function")
async def redis_client(test_redis_pool) -> AsyncGenerator[redis.Redis]:
    client = redis.Redis(connection_pool=test_redis_pool)
    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture(scope="session")
async def app(test_configuration, test_redis_pool):
    app = create_app(test_configuration, skip_lifespan=True)

    async def override_get_postgres_session():
        async with _shared_test_session.session_for_http_request() as session:
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

    app.dependency_overrides[get_configuration] = lambda: test_configuration
    app.dependency_overrides[get_postgres_session] = override_get_postgres_session
    app.dependency_overrides[get_autocommit_postgres_session] = override_get_postgres_session
    app.dependency_overrides[get_redis_client] = override_get_redis_client

    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _reset_dependency_overrides_between_tests(app):
    baseline = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(baseline)


@pytest_asyncio.fixture(scope="session")
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
