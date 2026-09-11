from redis.asyncio import Redis as AsyncRedis

from api.domain.provider.entities import Provider
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.utils.load_balancing import apply_async_load_balancing


async def apply_routing(
    providers: list[Provider],
    load_balancing_strategy: RouterLoadBalancingStrategy,
    redis_client: AsyncRedis,
) -> int:
    if len(providers) == 1:
        return providers[0].id

    return await apply_async_load_balancing(
        candidates=[provider.id for provider in providers],
        load_balancing_strategy=load_balancing_strategy,
        redis_client=redis_client,
    )
