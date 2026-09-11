from redis.asyncio import Redis as AsyncRedis

from api.helpers.load_balancing import LeastBusyLoadBalancingStrategy, ShuffleLoadBalancingStrategy
from api.schemas.admin.routers import RouterLoadBalancingStrategy


async def apply_async_load_balancing(
    load_balancing_strategy: RouterLoadBalancingStrategy,
    candidates: list[int],
    redis_client: AsyncRedis,
) -> int:
    if load_balancing_strategy == RouterLoadBalancingStrategy.LEAST_BUSY:
        strategy = LeastBusyLoadBalancingStrategy(redis_client=redis_client)
    else:
        strategy = ShuffleLoadBalancingStrategy()

    return await strategy.apply_async_strategy(candidates=candidates)
