from collections.abc import AsyncGenerator
import os

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
import redis.asyncio as redis

from api.app import create_app
from api.dependencies import get_autocommit_postgres_session, get_postgres_session, get_redis_client
from api.infrastructure.configuration import Configuration, Dependencies, Settings
from api.tests.helpers import TEST_AUTH_SECRET_KEY
from api.tests.integration.postgresfixtures import db_session, shared_test_session, test_postgres_engine  # noqa: F401
from api.tests.integration.redisfixtures import (  # noqa: F401
    _reset_redis_between_tests,
    redis_client,
    router_rate_limiter,
    test_redis_pool,
)


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


def pytest_addoption(parser):
    parser.addoption(
        "--commit-db",
        action="store_true",
        default=False,
        help="Commit DB changes after each test (for debugging with psql).",
    )


@pytest_asyncio.fixture(scope="session")
async def app(test_configuration, test_redis_pool):  # noqa: F811
    app = create_app(test_configuration, skip_lifespan=True)

    async def override_get_postgres_session():
        async with shared_test_session().session_for_http_request() as session:
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
