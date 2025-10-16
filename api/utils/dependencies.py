import redis.asyncio as redis
from redis.asyncio import Redis as AsyncRedis

from api.helpers.models import ModelRegistry
from api.utils.context import global_context


def get_model_registry() -> ModelRegistry:
    """
    Get the ModelRegistry instance from the global context.

    Returns:
        ModelRegistry: The ModelRegistry instance.
    """

    return global_context.model_registry


async def get_redis_client() -> AsyncRedis:
    """
    Get a Redis client built from the shared connection pool.

    Returns:
        AsyncRedis: A Redis client instance using the global connection pool.
    """

    client = await redis.Redis.from_pool(connection_pool=global_context.redis_pool)

    yield client

    await client.aclose()
