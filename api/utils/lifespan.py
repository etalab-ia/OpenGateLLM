from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from api.clients.parser import BaseParserClient as ParserClient
from api.helpers._documentmanager import DocumentManager
from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.helpers._identityaccessmanager import IdentityAccessManager
from api.helpers._limiter import Limiter
from api.helpers._parsermanager import ParserManager
from api.helpers._usagemanager import UsageManager
from api.helpers._usagetokenizer import UsageTokenizer
from api.helpers.models import ModelRegistry
from api.schemas.core.configuration import Configuration
from api.utils.configuration import get_configuration
from api.utils.context import global_context
from api.utils.exceptions import RouterNotFoundException
from api.utils.logging import init_logger

logger = init_logger(name=__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configuration = get_configuration()

    global_context.redis_pool = await create_redis_pool(configuration)
    global_context.elasticsearch_client = await create_elasticsearch_client(configuration)
    global_context.postgres_engine, global_context.postgres_session_factory = create_postgres_session_factory(configuration)
    global_context.model_registry = await create_model_registry(configuration, global_context.postgres_session_factory)
    global_context.elasticsearch_vector_store = await create_elasticsearch_vector_store(configuration, global_context.elasticsearch_client, global_context.model_registry, global_context.postgres_session_factory)  # fmt: off
    global_context.usage_manager = create_usage_manager()

    global_context.identity_access_manager = create_identity_access_manager(configuration=configuration)
    global_context.limiter = create_limiter(configuration=configuration, redis_pool=global_context.redis_pool)
    global_context.tokenizer = create_tokenizer(configuration=configuration)
    global_context.parser = await create_parser(configuration=configuration)
    global_context.document_manager = create_document_manager(configuration, elasticsearch_vector_store=global_context.elasticsearch_vector_store)

    await global_context.limiter.reset()

    yield

    if global_context.elasticsearch_client:
        await global_context.elasticsearch_client.close()

    if global_context.redis_pool:
        await global_context.redis_pool.aclose()

    if global_context.postgres_engine:
        await global_context.postgres_engine.dispose()


async def create_redis_pool(configuration: Configuration) -> redis.ConnectionPool:
    pool = redis.ConnectionPool.from_url(**configuration.dependencies.redis.model_dump())
    pool.url = configuration.dependencies.redis.url
    client = redis.Redis(connection_pool=pool)
    if not await client.ping():
        raise RuntimeError("Redis database is not reachable.")
    await client.aclose()
    return pool


async def create_elasticsearch_client(configuration: Configuration) -> AsyncElasticsearch | None:
    if configuration.dependencies.elasticsearch is None:
        return None

    kwargs = configuration.dependencies.elasticsearch.model_dump()
    kwargs.pop("index_name")
    kwargs.pop("index_language")
    kwargs.pop("number_of_shards")
    kwargs.pop("number_of_replicas")

    client = AsyncElasticsearch(**kwargs)
    if not await client.ping():
        await client.close()
        raise RuntimeError("Elasticsearch database is not reachable.")
    return client


def create_postgres_session_factory(configuration: Configuration) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(**configuration.dependencies.postgres.model_dump())
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


async def create_model_registry(
    configuration: Configuration,
    session_factory: async_sessionmaker,
) -> ModelRegistry:
    queuing_enabled = configuration.dependencies.celery is not None
    registry = ModelRegistry(
        app_title=configuration.settings.app_title,
        queuing_enabled=queuing_enabled,
        max_priority=configuration.settings.routing_max_priority,
        max_retries=configuration.settings.routing_max_retries,
        retry_countdown=configuration.settings.routing_retry_countdown,
    )
    async with session_factory() as session:
        await registry.setup(models=configuration.models, postgres_session=session)
    return registry


async def create_elasticsearch_vector_store(
    configuration: Configuration,
    elasticsearch_client: AsyncElasticsearch,
    model_registry: ModelRegistry,
    session_factory: async_sessionmaker,
) -> ElasticsearchVectorStore | None:
    if configuration.dependencies.elasticsearch is None or configuration.settings.vector_store_model is None:
        return None

    async with session_factory() as session:
        try:
            routers = await model_registry.get_routers(
                router_id=None,
                name=configuration.settings.vector_store_model,
                postgres_session=session,
            )
        except RouterNotFoundException:
            raise ValueError("Vector store model not found.")

    vector_size = routers[0].vector_size
    if vector_size is None:
        raise RuntimeError("Vector size is None (no provider for this model).")

    es_config = configuration.dependencies.elasticsearch
    vector_store = ElasticsearchVectorStore(index_name=es_config.index_name)
    await vector_store.setup(
        client=elasticsearch_client,
        index_language=es_config.index_language,
        number_of_shards=es_config.number_of_shards,
        number_of_replicas=es_config.number_of_replicas,
        vector_size=vector_size,
    )
    return vector_store


def create_usage_manager() -> UsageManager:
    return UsageManager()


def create_identity_access_manager(configuration: Configuration) -> IdentityAccessManager:
    return IdentityAccessManager(
        master_key=configuration.settings.auth_master_key,
        key_max_expiration_days=configuration.settings.auth_key_max_expiration_days,
        playground_session_duration=configuration.settings.auth_playground_session_duration,
    )


def create_limiter(configuration: Configuration, redis_pool: redis.ConnectionPool) -> Limiter:
    return Limiter(redis_pool=redis_pool, strategy=configuration.settings.rate_limiting_strategy)


def create_tokenizer(configuration: Configuration) -> UsageTokenizer:
    return UsageTokenizer(tokenizer=configuration.settings.usage_tokenizer)


async def create_parser(configuration: Configuration) -> ParserClient | None:
    if configuration.dependencies.parser is None:
        return None

    parser = ParserClient.import_module(type=configuration.dependencies.parser.type)(**configuration.dependencies.parser.model_dump())
    check_health = await parser.check_health()
    if not check_health:
        raise RuntimeError("Health check failed for parser.")
    return parser


def create_document_manager(configuration: Configuration, elasticsearch_vector_store: ElasticsearchVectorStore | None) -> DocumentManager | None:
    parser_manager = ParserManager(max_concurrent=configuration.settings.document_parsing_max_concurrent)
    return DocumentManager(vector_store_model=configuration.settings.vector_store_model, parser_manager=parser_manager)
