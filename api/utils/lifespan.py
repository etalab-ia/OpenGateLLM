from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

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
from api.schemas.core.context import GlobalContext
from api.utils.configuration import get_configuration
from api.utils.context import global_context
from api.utils.dependencies import get_elasticsearch_client, get_postgres_session
from api.utils.exceptions import RouterNotFoundException
from api.utils.logging import init_logger

logger = init_logger(name=__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    configuration = get_configuration()

    # setup global context
    await _setup_elasticsearch_client(configuration=configuration, global_context=global_context)
    await _setup_redis_pool(configuration=configuration, global_context=global_context)
    await _setup_postgres_session(configuration=configuration, global_context=global_context)

    await _setup_model_registry(configuration=configuration, global_context=global_context)
    await _setup_elasticsearch_vector_store(configuration=configuration, global_context=global_context)
    await _setup_usage_manager(configuration=configuration, global_context=global_context)
    await _setup_identity_access_manager(configuration=configuration, global_context=global_context)
    await _setup_limiter(configuration=configuration, global_context=global_context)
    await _setup_tokenizer(configuration=configuration, global_context=global_context)
    await _setup_parser(configuration=configuration, global_context=global_context)
    await _setup_document_manager(configuration=configuration, global_context=global_context)

    await global_context.limiter.reset()

    yield

    # cleanup resources when app shuts down
    if global_context.elasticsearch_client:
        await global_context.elasticsearch_client.close()


async def _setup_elasticsearch_client(configuration: Configuration, global_context: GlobalContext):
    if configuration.dependencies.elasticsearch is None:
        global_context.elasticsearch_client = None
        return

    kwargs = configuration.dependencies.elasticsearch.model_dump()
    kwargs.pop("index_name")
    kwargs.pop("index_language")
    kwargs.pop("number_of_shards")
    kwargs.pop("number_of_replicas")
    global_context.elasticsearch_client = AsyncElasticsearch(**kwargs)

    assert await global_context.elasticsearch_client.ping(), "Elasticsearch database is not reachable."


async def _setup_elasticsearch_vector_store(configuration: Configuration, global_context: GlobalContext):
    assert global_context.model_registry, "Set model registry in global context before setting up Elasticsearch manager."

    if configuration.dependencies.elasticsearch is None:
        global_context.elasticsearch_vector_store = None
        return

    elasticsearch_client = get_elasticsearch_client()

    async for postgres_session in get_postgres_session():
        try:
            routers = await global_context.model_registry.get_routers(
                router_id=None,
                name=configuration.settings.vector_store_model,
                postgres_session=postgres_session,
            )
        except RouterNotFoundException:
            raise ValueError("Vector store model not found.")

        router = routers[0]
        vector_size = router.vector_size
        assert vector_size is not None, "Vector size is None (no provider for this model)."

    elasticsearch_vector_store = ElasticsearchVectorStore(index_name=configuration.dependencies.elasticsearch.index_name)
    await elasticsearch_vector_store.setup(
        client=elasticsearch_client,
        index_language=configuration.dependencies.elasticsearch.index_language,
        number_of_shards=configuration.dependencies.elasticsearch.number_of_shards,
        number_of_replicas=configuration.dependencies.elasticsearch.number_of_replicas,
        vector_size=vector_size,
    )
    global_context.elasticsearch_vector_store = elasticsearch_vector_store


async def _setup_redis_pool(configuration: Configuration, global_context: GlobalContext):
    redis_pool = redis.ConnectionPool.from_url(**configuration.dependencies.redis.model_dump())
    redis_pool.url = configuration.dependencies.redis.url  # for celery

    # check if redis is reachable
    redis_client = redis.Redis(connection_pool=redis_pool)
    ping = await redis_client.ping()
    assert ping, "Redis database is not reachable."
    await redis_client.aclose()

    global_context.redis_pool = redis_pool


async def _setup_usage_manager(configuration: Configuration, global_context: GlobalContext):
    global_context.usage_manager = UsageManager()


async def _setup_postgres_session(configuration: Configuration, global_context: GlobalContext):
    """Set up the PostgreSQL session by creating the session pool."""

    engine = create_async_engine(**configuration.dependencies.postgres.model_dump())
    postgres_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    global_context.postgres_session_factory = postgres_session_factory


async def _setup_model_registry(configuration: Configuration, global_context: GlobalContext):
    """Setup the model registry by fetching the models defined in the DB and the configuration. Basic conflict handling between the DB and config."""
    queuing_enabled = configuration.dependencies.celery is not None
    async for postgres_session in get_postgres_session():
        global_context.model_registry = ModelRegistry(
            app_title=configuration.settings.app_title,
            queuing_enabled=queuing_enabled,
            max_priority=configuration.settings.routing_max_priority,
            max_retries=configuration.settings.routing_max_retries,
            retry_countdown=configuration.settings.routing_retry_countdown,
        )
        await global_context.model_registry.setup(models=configuration.models, postgres_session=postgres_session)


async def _setup_identity_access_manager(configuration: Configuration, global_context: GlobalContext):
    global_context.identity_access_manager = IdentityAccessManager(
        master_key=configuration.settings.auth_master_key,
        key_max_expiration_days=configuration.settings.auth_key_max_expiration_days,
        playground_session_duration=configuration.settings.auth_playground_session_duration,
    )


async def _setup_limiter(configuration: Configuration, global_context: GlobalContext):
    global_context.limiter = Limiter(redis_pool=global_context.redis_pool, strategy=configuration.settings.rate_limiting_strategy)


async def _setup_tokenizer(configuration: Configuration, global_context: GlobalContext):
    global_context.tokenizer = UsageTokenizer(tokenizer=configuration.settings.usage_tokenizer)


async def _setup_parser(configuration: Configuration, global_context: GlobalContext):
    if configuration.dependencies.parser is None:
        global_context.parser = None
    else:
        parser = ParserClient.import_module(type=configuration.dependencies.parser.type)(**configuration.dependencies.parser.model_dump())
        check_health = await parser.check_health()
        assert check_health, "Health check failed for parser."
        global_context.parser = parser


async def _setup_document_manager(configuration: Configuration, global_context: GlobalContext):
    if global_context.elasticsearch_vector_store is None:
        global_context.document_manager = None
        return

    parser_manager = ParserManager(max_concurrent=configuration.settings.document_parsing_max_concurrent)
    global_context.document_manager = DocumentManager(vector_store_model=configuration.settings.vector_store_model, parser_manager=parser_manager)
