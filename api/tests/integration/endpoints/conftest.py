import pytest_asyncio
import redis.asyncio as redis


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _restore_dependency_overrides(app):
    snapshot = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(snapshot)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _reset_redis_between_tests(test_redis_pool):
    client = redis.Redis(connection_pool=test_redis_pool)
    try:
        await client.flushdb()
        yield
        await client.flushdb()
    finally:
        await client.aclose()
