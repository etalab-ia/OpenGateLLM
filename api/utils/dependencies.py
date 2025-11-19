from contextvars import ContextVar

import redis.asyncio as redis
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._usagemanager import UsageManager
from api.helpers.models import ModelRegistry
from api.schemas.core.context import RequestContext
from api.utils.context import global_context, request_context


def get_request_context() -> ContextVar[RequestContext]:
    """
    Get the RequestContext ContextVar from the global context.

    Returns:
        ContextVar[RequestContext]: The RequestContext ContextVar instance.
    """

    return request_context


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


async def get_postgres_session() -> AsyncSession:
    """
    Get a PostgreSQL postgres_session from the global context.

    Returns:
        AsyncSession: A PostgreSQL postgres_session instance.
    """

    session_factory = global_context.postgres_session_factory
    async with session_factory() as postgres_session:
        yield postgres_session

        if postgres_session.in_transaction():
            await postgres_session.close()


async def get_usage_manager() -> UsageManager:
    """
    Get the UsageManager instance from the global context.

    Returns:
        UsageManager: The UsageManager instance.
    """

    return global_context.usage_manager
