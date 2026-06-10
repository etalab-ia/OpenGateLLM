from unittest.mock import patch

import pytest
from redis.asyncio import Redis as AsyncRedis

from api.domain.provider.entities import Provider, ProviderType
from api.domain.router.entities import RouterLoadBalancingStrategy
from api.infrastructure.redis._redisproviderloadbalancer import RedisProviderLoadBalancer
from api.tests.integration.factories.redis import MetricsRedisFactory


def provider(provider_id: int) -> Provider:
    return Provider(
        id=provider_id,
        router_id=1,
        user_id=1,
        type=ProviderType.VLLM,
        url="http://test",
        timeout=30,
        model_name="test-model",
        created=0,
        updated=0,
    )


@pytest.fixture
def load_balancer(redis_client):
    return RedisProviderLoadBalancer(redis_client=redis_client)


@pytest.mark.asyncio(loop_scope="session")
class TestRedisProviderLoadBalancer:
    async def test_shuffle_returns_provider_from_list(self, load_balancer: RedisProviderLoadBalancer):
        # Arrange
        providers = [provider(1), provider(2), provider(3)]

        # Act
        with patch("api.infrastructure.redis._redisproviderloadbalancer.random.choice", return_value=providers[1]):
            result = await load_balancer.find_best_provider(strategy=RouterLoadBalancingStrategy.SHUFFLE, providers=providers)

        # Assert
        assert result == providers[1]

    async def test_least_busy_returns_single_provider(self, load_balancer: RedisProviderLoadBalancer):
        # Arrange
        providers = [provider(10)]

        # Act
        result = await load_balancer.find_best_provider(strategy=RouterLoadBalancingStrategy.LEAST_BUSY, providers=providers)

        # Assert
        assert result == providers[0]

    async def test_least_busy_returns_provider_when_inflight_is_zero(self, load_balancer: RedisProviderLoadBalancer, redis_client: AsyncRedis):
        # Arrange
        busy_provider = provider(32)
        idle_provider = provider(33)
        await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=busy_provider.id, value=4)
        await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=idle_provider.id, value=0)

        # Act
        result = await load_balancer.find_best_provider(
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            providers=[busy_provider, idle_provider],
        )

        # Assert
        assert result == idle_provider

    async def test_least_busy_returns_provider_when_inflight_key_missing(self, load_balancer: RedisProviderLoadBalancer, redis_client: AsyncRedis):
        # Arrange
        provider_with_inflight_key = provider(30)
        provider_without_inflight_key = provider(31)
        await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=provider_with_inflight_key.id, value=5)

        # Act
        result = await load_balancer.find_best_provider(
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            providers=[provider_with_inflight_key, provider_without_inflight_key],
        )

        # Assert
        assert result == provider_without_inflight_key

    async def test_least_busy_returns_provider_with_lowest_inflight_count(self, load_balancer: RedisProviderLoadBalancer, redis_client: AsyncRedis):
        # Arrange
        providers = [provider(40), provider(41), provider(42)]
        await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=providers[0].id, value=7)
        await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=providers[1].id, value=2)
        await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=providers[2].id, value=5)

        # Act
        with patch("api.infrastructure.redis._redisproviderloadbalancer.random.choice", return_value=providers[1]):
            result = await load_balancer.find_best_provider(strategy=RouterLoadBalancingStrategy.LEAST_BUSY, providers=providers)

        # Assert
        assert result == providers[1]

    async def test_least_busy_picks_among_tied_minimum_inflight_providers(self, load_balancer: RedisProviderLoadBalancer, redis_client: AsyncRedis):
        # Arrange
        providers = [provider(50), provider(51), provider(52)]
        await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=providers[0].id, value=3)
        await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=providers[1].id, value=8)
        await MetricsRedisFactory.set_inflight(redis_client=redis_client, provider_id=providers[2].id, value=3)

        # Act
        with patch("api.infrastructure.redis._redisproviderloadbalancer.random.choice", return_value=providers[2]) as mock_choice:
            result = await load_balancer.find_best_provider(strategy=RouterLoadBalancingStrategy.LEAST_BUSY, providers=providers)

        # Assert
        assert result == providers[2]
        mock_choice.assert_called_once()
        tied_candidates = mock_choice.call_args[0][0]
        assert {candidate.id for candidate in tied_candidates} == {providers[0].id, providers[2].id}
        assert all(isinstance(candidate, Provider) for candidate in tied_candidates)
