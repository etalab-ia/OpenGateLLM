from collections.abc import AsyncGenerator
import os

from fastapi import BackgroundTasks
import pytest
import pytest_asyncio
import redis.asyncio as redis

from api.domain.router import RouterRateLimiter
from api.infrastructure.redis import RedisRouterRateLimiter


def _test_redis_url() -> str:
    url = os.getenv("TEST_REDIS_URL", "redis://:changeme@localhost:6379/1")
    xdist_worker = os.getenv("PYTEST_XDIST_WORKER")
    if not xdist_worker:
        return url
    base_url, db = url.rsplit("/", 1)
    xdist_worker_index = int(xdist_worker.removeprefix("gw"))
    return f"{base_url}/{int(db) + xdist_worker_index}"


TEST_REDIS_URL = _test_redis_url()


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


@pytest_asyncio.fixture(scope="function")
async def redis_client(test_redis_pool) -> AsyncGenerator[redis.Redis]:
    client = redis.Redis(connection_pool=test_redis_pool)
    try:
        yield client
    finally:
        await client.aclose()
