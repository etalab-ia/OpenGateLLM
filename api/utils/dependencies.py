from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Any

from elasticsearch import AsyncElasticsearch
import redis.asyncio as redis
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.helpers._usagemanager import UsageManager
from api.helpers.models import ModelRegistry
from api.schemas.core.context import RequestContext
from api.utils.context import global_context, request_context
from api.utils.exceptions import FeatureNotEnabledException


def get_request_context() -> ContextVar[RequestContext]:
    """
    Get the RequestContext ContextVar from the global context.

    Returns:
        ContextVar[RequestContext]: The RequestContext ContextVar instance.
    """

    return request_context


async def get_redis_client() -> AsyncGenerator[Redis, Any]:
    """
    Get a Redis client built from the shared connection pool.

    Returns:
        AsyncRedis: A Redis client instance using the global connection pool.
    """

    client = redis.Redis(connection_pool=global_context.redis_pool)

    yield client

    await client.aclose()


async def get_postgres_session() -> AsyncGenerator[AsyncSession | Any, Any]:
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


def get_elasticsearch_client() -> AsyncElasticsearch:
    """
    Get an Elasticsearch client from the global context (singleton pattern, Elasticsearch is thread-safe).

    Returns:
        AsyncElasticsearch: An Elasticsearch client instance.
    """

    return global_context.elasticsearch_client


def get_elasticsearch_vector_store() -> ElasticsearchVectorStore:
    """
    Get the ElasticsearchVectorStore instance from the global context.
    """

    if not global_context.elasticsearch_vector_store:
        raise FeatureNotEnabledException()

    return global_context.elasticsearch_vector_store


def get_model_registry() -> ModelRegistry:
    """
    Get the ModelRegistry instance from the global context.

    Returns:
        ModelRegistry: The ModelRegistry instance.
    """

    return global_context.model_registry


async def get_usage_manager() -> UsageManager:
    """
    Get the UsageManager instance from the global context.

    Returns:
        UsageManager: The UsageManager instance.
    """

    return global_context.usage_manager
