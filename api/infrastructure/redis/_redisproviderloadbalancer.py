import random

from redis.asyncio import Redis as AsyncRedis

from api.domain.provider import ProviderLoadBalancer
from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy
from api.utils.variables import PREFIX__REDIS_METRIC_GAUGE


class RedisProviderLoadBalancer(ProviderLoadBalancer):
    def __init__(self, redis_client: AsyncRedis):
        self.redis_client = redis_client

    async def find_best_provider(self, strategy: RouterLoadBalancingStrategy, providers: list[Provider]) -> Provider:
        match strategy:
            case RouterLoadBalancingStrategy.SHUFFLE:
                return await self._apply_shuffle_strategy(providers)
            case RouterLoadBalancingStrategy.LEAST_BUSY:
                return await self._apply_least_busy_strategy(providers)

    async def _apply_shuffle_strategy(self, providers: list[Provider]) -> Provider:
        return random.choice(providers)

    async def _apply_least_busy_strategy(self, providers: list[Provider]) -> Provider:
        if len(providers) == 1:
            return providers[0]

        inflight_counts = {}
        for provider in providers:
            key = f"{PREFIX__REDIS_METRIC_GAUGE}:inflight:{provider.id}"
            if not await self.redis_client.exists(key):
                return provider  # avoid to retrieve other provider if one has no inflight requests

            value = await self.redis_client.get(key)
            inflight_counts[provider.id] = int(value) if value is not None else 0
            if inflight_counts[provider.id] == 0:
                return provider  # avoid to retrieve other provider if one has no inflight requests

        min_inflight_count = min(inflight_counts.values())
        candidates = [provider for provider in providers if inflight_counts[provider.id] == min_inflight_count]

        return random.choice(candidates)
