import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def _restore_dependency_overrides():
    yield


@pytest_asyncio.fixture(autouse=True)
async def _reset_redis_between_tests():
    yield
