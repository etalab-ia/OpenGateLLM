from collections.abc import AsyncGenerator

import asyncpg
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from api.app import create_app
from api.dependencies import get_postgres_session
from api.helpers.models import ModelRegistry
from api.schemas.core.configuration import Configuration, Dependencies, Settings
from api.sql.models import Base
from api.tests.integration import factories
from api.utils.dependencies import get_model_registry
from api.utils.dependencies import get_postgres_session as get_postgres_session_utils

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:changeme@localhost:5432/test_db"


@pytest.fixture
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
            session_secret_key="test-secret-key",
            disabled_routers=[],
            hidden_routers=[],
            monitoring_prometheus_enabled=False,
        ),
        dependencies=Dependencies.model_construct(sentry=None),
    )
    return configuration


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


def _all_sql_factories():
    result = []
    stack = list(factories.BaseSQLFactory.__subclasses__())
    while stack:
        cls = stack.pop()
        result.append(cls)
        stack.extend(cls.__subclasses__())
    return result


# @pytest_asyncio.fixture(scope="session")
# async def test_session_factory(test_engine):
#     return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

#
# @pytest_asyncio.fixture(scope="function")
# async def db_session(test_session_factory) -> AsyncGenerator[AsyncSession]:
#     async with test_session_factory() as session:
#         all_sql_factories = factories.BaseSQLFactory.__subclasses__()
#         session.expire_on_commit = False
#         try:
#             async with session.begin_nested():
#                 for factory in all_sql_factories:
#                     factory._meta.sqlalchemy_session = session
#                 yield session
#         finally:
#             if session.in_transaction():
#                 await session.rollback()
#             await session.close()


def pytest_addoption(parser):
    parser.addoption(
        "--commit-db",
        action="store_true",
        default=False,
        help="Commit DB changes after each test (for debugging with psql).",
    )


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine, request) -> AsyncGenerator[AsyncSession]:
    async with test_engine.connect() as connection:
        transaction = await connection.begin()

        session = AsyncSession(bind=connection, expire_on_commit=False)
        await session.begin_nested()

        all_sql_factories = _all_sql_factories()
        for factory in all_sql_factories:
            factory._meta.sqlalchemy_session = session

        @event.listens_for(session.sync_session, "after_transaction_end")
        def restart_savepoint(sess, trans):
            if trans.nested and not trans._parent.nested:
                sess.begin_nested()

        try:
            yield session
        finally:
            event.remove(session.sync_session, "after_transaction_end", restart_savepoint)
            for factory in all_sql_factories:
                factory._meta.sqlalchemy_session = None
            await session.close()
            if request.config.getoption("--commit-db"):
                await transaction.commit()
            else:
                await transaction.rollback()


@pytest_asyncio.fixture(scope="session")
def model_registry():
    return ModelRegistry(
        app_title="test",
        queuing_enabled=False,
        max_priority=0,
        max_retries=0,
        retry_countdown=0,
    )


@pytest_asyncio.fixture(scope="function")
async def app(db_session, model_registry, test_configuration):
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
    app.dependency_overrides[get_postgres_session_utils] = override_get_postgres_session
    app.dependency_overrides[get_model_registry] = lambda: model_registry

    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
