import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Iterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager, contextmanager
import os

import asyncpg
import pytest_asyncio
from sqlalchemy import event, make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine

from api.infrastructure.postgres import PostgresUsageRepository
from api.infrastructure.postgres.models import Base
from api.tests.integration import factories
from api.tests.integration.globalcontext import override_global_context


def _test_postgres_url() -> str:
    url = make_url(os.getenv("TEST_POSTGRES_URL", "postgresql+asyncpg://postgres:changeme@localhost:5432/test_db"))
    xdist_worker = os.getenv("PYTEST_XDIST_WORKER")
    if xdist_worker and url.database:
        url = url.set(database=f"{url.database}_{xdist_worker}")
    return url.render_as_string(hide_password=False)


TEST_POSTGRES_URL = _test_postgres_url()

_shared_test_session: "SharedTestSession | None" = None


def shared_test_session() -> "SharedTestSession":
    return _shared_test_session


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
def bind_sql_factories(session):
    all_factories = _all_sql_factories()
    for factory in all_factories:
        factory._meta.sqlalchemy_session = session
    try:
        yield
    finally:
        for factory in all_factories:
            factory._meta.sqlalchemy_session = None


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
