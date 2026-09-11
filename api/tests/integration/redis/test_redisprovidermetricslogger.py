import pytest
from redis.asyncio import Redis as AsyncRedis

from api.infrastructure.redis._redisprovidermetricslogger import RedisProviderMetricsLogger
from api.tests.integration.factories.redis import MetricsRedisFactory


@pytest.fixture
def repository(redis_client):
    return RedisProviderMetricsLogger(redis_client=redis_client)


@pytest.mark.asyncio(loop_scope="session")
class TestRedisProviderMetricsLogger:
    async def test_increment_inflight(self, repository: RedisProviderMetricsLogger, redis_client: AsyncRedis):
        # Arrange
        provider_id = 44
        key = await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=provider_id, value=10)

        # Act
        incremented = await repository.increment_inflight(provider_id=provider_id)

        # Assert
        assert incremented is True
        value = await repository.redis_client.get(key)
        assert int(value) == 11

    async def test_decrement_inflight(self, repository, redis_client: AsyncRedis):
        # Arrange
        provider_id = 44
        key = await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=provider_id, value=4)

        # Act
        await repository.decrement_inflight(provider_id=provider_id)
        value = await repository.redis_client.get(key)

        # Assert
        assert int(value) == 3
