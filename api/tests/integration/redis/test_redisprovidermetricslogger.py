import pytest
from redis.asyncio import Redis as AsyncRedis

from api.domain.provider.entities import Metric
from api.infrastructure.redis._redisprovidermetricslogger import RedisProviderMetricsLogger
from api.tests.integration.factories.redis import MetricsRedisFactory
from api.utils.variables import PREFIX__REDIS_METRIC_TIMESERIE


@pytest.fixture
def repository(redis_client):
    return RedisProviderMetricsLogger(redis_client=redis_client)


@pytest.mark.asyncio(loop_scope="session")
class TestRedisProviderMetricsLogger:
    @pytest.mark.parametrize("metric", [Metric.TTFT, Metric.LATENCY])
    async def test_log_multiple_metric(self, repository: RedisProviderMetricsLogger, redis_client: AsyncRedis, metric: Metric):
        # Arrange
        provider_id = 42
        key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{metric.value}:{provider_id}"

        # Act
        await repository.log_metric(provider_id=provider_id, metric=metric.TTFT, value=120)
        await repository.log_metric(provider_id=provider_id, metric=metric.TTFT, value=240)

        # Assert
        values = await redis_client.ts().range(key=key, from_time="-", to_time="+")
        assert len(values) == 2
        assert values[0][1] == 120
        assert values[1][1] == 240

    @pytest.mark.parametrize("metric", [Metric.TTFT, Metric.LATENCY])
    async def test_get_metric_history(self, repository, redis_client: AsyncRedis, metric: Metric):
        # Arrange
        provider_id = 43

        await MetricsRedisFactory.set_metric(redis_client=redis_client, provider_id=provider_id, metric=metric, values=[100, 200.0])
        # Act
        result = await repository.get_metric_history(provider_id=provider_id, metric=metric)

        # Assert
        assert result == [100.0, 200.0]

    async def test_get_metric_history_returns_empty_list_when_key_missing(self, repository):
        # Act
        result = await repository.get_metric_history(provider_id=9999, metric=Metric.TTFT)

        # Assert
        assert result == []

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
        decremented = await repository.decrement_inflight(provider_id=provider_id, inflight_is_incremented=True)
        value = await repository.redis_client.get(key)

        # Assert
        assert decremented is True
        assert int(value) == 3

    async def test_decrement_inflight_does_nothing_when_not_incremented(self, repository):
        # Arrange
        provider_id = 45

        # Act
        await repository.decrement_inflight(provider_id=provider_id, inflight_is_incremented=False)
        current_inflight = await repository.get_current_inflight(provider_id=provider_id)

        # Assert
        assert current_inflight == 0
