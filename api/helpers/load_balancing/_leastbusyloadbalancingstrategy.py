import random

from redis.asyncio import Redis as AsyncRedis

from api.utils.variables import PREFIX__REDIS_METRIC_GAUGE

from ._baseloadbalancingstrategy import BaseLoadBalancingStrategy


class LeastBusyLoadBalancingStrategy(BaseLoadBalancingStrategy):
    def __init__(self, redis_client: AsyncRedis) -> None:
        self.redis_client = redis_client

    async def apply_async_strategy(self, candidates: list[int]) -> int:
        if len(candidates) == 1:
            return candidates[0]

        inflight_counts = {}
        for provider_id in candidates:
            key = f"{PREFIX__REDIS_METRIC_GAUGE}:inflight:{provider_id}"
            if not await self.redis_client.exists(key):
                return provider_id

            value = await self.redis_client.get(key)
            inflight_counts[provider_id] = int(value) if value is not None else 0
            if inflight_counts[provider_id] == 0:
                return provider_id

        min_inflight_count = min(inflight_counts.values())
        tied = [provider_id for provider_id, count in inflight_counts.items() if count == min_inflight_count]
        return random.choice(tied)
