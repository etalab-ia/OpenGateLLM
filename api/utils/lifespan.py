from contextlib import asynccontextmanager
import traceback
from types import SimpleNamespace

from fastapi import FastAPI
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.clients.parser import BaseParserClient as ParserClient
from api.clients.vector_store import BaseVectorStoreClient as VectorStoreClient
from api.clients.web_search_engine import BaseWebSearchEngineClient as WebSearchEngineClient
from api.helpers._documentmanager import DocumentManager
from api.helpers._identityaccessmanager import IdentityAccessManager
from api.helpers._limiter import Limiter
from api.helpers._parsermanager import ParserManager
from api.helpers._usagemanager import UsageManager
from api.helpers._usagetokenizer import UsageTokenizer
from api.helpers._websearchmanager import WebSearchManager
from api.helpers.models import ModelRegistry
from api.schemas.core.configuration import Configuration
from api.schemas.core.context import GlobalContext
from api.utils.configuration import get_configuration
from api.utils.context import global_context
from api.utils.dependencies import get_postgres_session
from api.utils.logging import init_logger

logger = init_logger(name=__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    configuration = get_configuration()

    # Dependencies
    parser = ParserClient.import_module(type=configuration.dependencies.parser.type)(**configuration.dependencies.parser.model_dump()) if configuration.dependencies.parser else None  # fmt: off
    vector_store = VectorStoreClient.import_module(type=configuration.dependencies.vector_store.type)(**configuration.dependencies.vector_store.model_dump()) if configuration.dependencies.vector_store else None  # fmt: off
    web_search_engine = WebSearchEngineClient.import_module(type=configuration.dependencies.web_search_engine.type)(**configuration.dependencies.web_search_engine.model_dump()) if configuration.dependencies.web_search_engine else None  # fmt: off

    assert await vector_store.check() if vector_store else True, "Vector store database is not reachable."

    dependencies = SimpleNamespace(parser=parser, vector_store=vector_store, web_search_engine=web_search_engine)

    # perform async health checks for external dependencies when possible
    try:
        if dependencies.parser and hasattr(dependencies.parser, "check_health"):
            await dependencies.parser.check_health()
    except Exception:
        # Log an error with the parser client class name for easier debugging
        parser_name = getattr(dependencies.parser, "__class__", None)
        parser_name = parser_name.__name__ if parser_name else "parser"
        logger.error(msg=f"Health check failed for parser '{parser_name}': {traceback.format_exc()}")

    # setup global context
    await _setup_redis_pool(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_usage_manager(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_postgres_session(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_model_registry(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_identity_access_manager(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_limiter(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_tokenizer(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_document_manager(configuration=configuration, global_context=global_context, dependencies=dependencies)

    yield

    # cleanup resources when app shuts down
    if vector_store:
        await vector_store.close()


async def _setup_redis_pool(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    redis_pool = redis.ConnectionPool.from_url(url=configuration.dependencies.redis.url)
    redis_pool.url = configuration.dependencies.redis.url

    # check if redis is reachable
    redis_client = redis.Redis.from_pool(connection_pool=redis_pool)
    ping = await redis_client.ping()
    assert ping, "Redis database is not reachable."
    await redis_client.aclose()

    global_context.redis_pool = redis_pool


async def _setup_usage_manager(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    global_context.usage_manager = UsageManager()


async def _setup_postgres_session(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    """Setup the PostgreSQL session by creating the session pool."""

    engine = create_async_engine(**configuration.dependencies.postgres.model_dump())
    postgres_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    global_context.postgres_session_factory = postgres_session_factory


async def _setup_model_registry(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
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


async def _setup_identity_access_manager(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    global_context.identity_access_manager = IdentityAccessManager(
        master_key=configuration.settings.auth_master_key,
        key_max_expiration_days=configuration.settings.auth_key_max_expiration_days,
        playground_session_duration=configuration.settings.auth_playground_session_duration,
    )


async def _setup_limiter(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    global_context.limiter = Limiter(redis_pool=global_context.redis_pool, strategy=configuration.settings.rate_limiting_strategy)


async def _setup_tokenizer(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    global_context.tokenizer = UsageTokenizer(tokenizer=configuration.settings.usage_tokenizer)


async def _setup_document_manager(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    assert global_context.model_registry, "Set model registry in global context before setting up document manager."

    web_search_manager, parser_manager = None, None

    if dependencies.vector_store is None:
        global_context.document_manager = None
        return

    async for postgres_session in get_postgres_session():
        router_id = await global_context.model_registry.get_router_id_from_model_name(
            model_name=configuration.settings.vector_store_model,
            postgres_session=postgres_session,
        )
    assert router_id is not None, "Vector store model not found."

    global_context.document_manager = DocumentManager(
        vector_store=dependencies.vector_store,
        vector_store_model=configuration.settings.vector_store_model,
        parser_manager=parser_manager,
        web_search_manager=web_search_manager,
    )

    if dependencies.web_search_engine:
        web_search_manager = WebSearchManager(
            web_search_engine=dependencies.web_search_engine,
            query_model=configuration.settings.search_web_query_model,
            limited_domains=configuration.settings.search_web_limited_domains,
            user_agent=configuration.settings.search_web_user_agent,
        )

    parser_manager = ParserManager(parser=dependencies.parser)

    global_context.document_manager = DocumentManager(
        vector_store=dependencies.vector_store,
        vector_store_model=configuration.settings.vector_store_model,
        parser_manager=parser_manager,
        web_search_manager=web_search_manager,
    )
