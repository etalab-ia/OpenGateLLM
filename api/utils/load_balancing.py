from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from api.helpers.load_balancing import LeastBusyLoadBalancingStrategy, ShuffleLoadBalancingStrategy
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.core.metrics import Metric


def apply_sync_load_balancing(
    load_balancing_strategy: RouterLoadBalancingStrategy,
    candidates: list[int],
    redis_client: Redis,
    load_balancing_metric: Metric = Metric.TTFT,
) -> tuple[int, float | None]:
    """
    Get a provider to handle the request based on the specified routing strategy.

    Args:
        load_balancing_strategy (RouterLoadBalancingStrategy): The routing strategy to use for selecting a provider
        candidates (list[int]): The list of provider candidates (provider IDs) to choose from
        redis_client (Redis): Redis client instance, required for least busy strategy
        load_balancing_metric (Metric): The type of metric to use for performance evaluation

    Returns:
        tuple[int, float | None]: A tuple containing:
            - provider_id (int): The chosen provider ID
            - performance_indicator (float | None): Performance metric for the chosen provider, if applicable
    """
    if load_balancing_strategy == RouterLoadBalancingStrategy.LEAST_BUSY:
        load_balancing_strategy = LeastBusyLoadBalancingStrategy(redis_client=redis_client, load_balancing_metric=load_balancing_metric)
    else:  # load_balancing_strategy == RouterLoadBalancingStrategy.SHUFFLE:
        load_balancing_strategy = ShuffleLoadBalancingStrategy()

    provider_id, performance_indicator = load_balancing_strategy.apply_sync_strategy(candidates=candidates)

    return provider_id, performance_indicator


async def apply_async_load_balancing(
    load_balancing_strategy: RouterLoadBalancingStrategy,
    candidates: list[int],
    redis_client: AsyncRedis | None = None,
    load_balancing_metric: Metric = Metric.TTFT,
) -> tuple[int, float | None]:
    """
    Get a provider to handle the request based on the specified routing strategy.

    Args:
        load_balancing_strategy (RouterLoadBalancingStrategy): The routing strategy to use for selecting a provider
        candidates (list[int]): The list of provider candidates (provider IDs) to choose from
        redis_client (AsyncRedis | None): Redis client instance, required for least busy strategy
        load_balancing_metric (Metric): The type of metric to use for performance evaluation

    Returns:
        tuple[int, float | None]: A tuple containing:
            - provider_id (int): The chosen provider ID
            - performance_indicator (float | None): Performance metric for the chosen provider, if applicable
    """
    performance_indicator = None
    if load_balancing_strategy == RouterLoadBalancingStrategy.LEAST_BUSY:
        load_balancing_strategy = LeastBusyLoadBalancingStrategy(redis_client=redis_client, load_balancing_metric=load_balancing_metric)
    else:  # load_balancing_strategy == RouterLoadBalancingStrategy.SHUFFLE:
        load_balancing_strategy = ShuffleLoadBalancingStrategy()

    provider_id, performance_indicator = await load_balancing_strategy.apply_async_strategy(candidates=candidates)

    return provider_id, performance_indicator
