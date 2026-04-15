from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
import tiktoken
from tiktoken.core import Encoding

from api.clients.parser import BaseParserClient as ParserClient
from api.dependencies import get_postgres_session
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider.errors import ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router.errors import RouterNameAlreadyExistsError
from api.helpers._documentmanager import DocumentManager
from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.helpers._identityaccessmanager import IdentityAccessManager
from api.helpers._limiter import Limiter
from api.helpers._parsermanager import ParserManager
from api.helpers._usagemanager import UsageManager
from api.helpers._usagetokenizer import UsageTokenizer
from api.helpers.models import ModelRegistry
from api.infrastructure.fastapi.context import RequestContextManager
from api.infrastructure.http.model import ModelMetricsLogger
from api.infrastructure.model import ModelProviderGateway
from api.infrastructure.postgres import (
    PostgresLimitRepository,
    PostgresPermissionRepository,
    PostgresProviderRepository,
    PostgresRolesRepository,
    PostgresRouterRepository,
    PostgresUserRepository,
)
from api.schemas.core.configuration import Configuration, Tokenizer
from api.use_cases.admin.bootstrapadminusecase import (
    BootstrapAdminCommand,
    BootstrapAdminUseCase,
    BootstrapAdminUseCaseSkipped,
    BootstrapAdminUseCaseSuccess,
)
from api.use_cases.models import BootstrapModelsUseCase, BootstrapModelsUseCaseSkipped, BootstrapModelsUseCaseSuccess
from api.utils.configuration import get_configuration
from api.utils.context import global_context
from api.utils.exceptions import RouterNotFoundException
from api.utils.logging import init_logger

logger = init_logger(name=__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configuration = get_configuration()

    global_context.redis_pool = await create_redis_pool(configuration)
    global_context.elasticsearch_client = await create_elasticsearch_client(configuration)
    global_context.postgres_engine, global_context.postgres_session_factory = create_postgres_session_factory(configuration)

    async for postgres_session in get_postgres_session():
        bootstrap_admin_user_id = await bootstrap_admin_role_and_user(configuration=configuration, postgres_session=postgres_session)
        await bootstrap_models(configuration=configuration, postgres_session=postgres_session, bootstrap_admin_user_id=bootstrap_admin_user_id)

    global_context.model_registry = await create_model_registry(configuration, global_context.postgres_session_factory)
    global_context.elasticsearch_vector_store = await create_elasticsearch_vector_store(configuration, global_context.elasticsearch_client, global_context.model_registry, global_context.postgres_session_factory)  # fmt: off
    global_context.usage_manager = create_usage_manager()
    global_context.identity_access_manager = create_identity_access_manager(configuration=configuration)
    global_context.limiter = create_limiter(configuration=configuration, redis_pool=global_context.redis_pool)
    global_context.tokenizer = create_tokenizer(configuration=configuration)
    global_context._tokenizer = initialize_tokenizer(configuration=configuration)
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


async def bootstrap_admin_role_and_user(configuration: Configuration, postgres_session: AsyncSession) -> int:
    user_repository = PostgresUserRepository(postgres_session=postgres_session)
    role_repository = PostgresRolesRepository(postgres_session=postgres_session)
    limit_repository = PostgresLimitRepository(postgres_session=postgres_session)
    permission_repository = PostgresPermissionRepository(postgres_session=postgres_session)

    result = await BootstrapAdminUseCase(
        user_repository=user_repository,
        role_repository=role_repository,
        limit_repository=limit_repository,
        permission_repository=permission_repository,
    ).execute(
        BootstrapAdminCommand(email=configuration.settings.auth_bootsrap_admin_username, password=configuration.settings.auth_bootsrap_admin_password)
    )

    match result:
        case BootstrapAdminUseCaseSuccess() as success:
            logger.info(f"Admin user not found, bootstrap admin created ({success.email}):")
            logger.info(f"user ID: {success.user_id}")
            logger.info(f"role ID: {success.role_id}")
            return success.user_id
        case BootstrapAdminUseCaseSkipped() as skipped:
            logger.info(f"Admin user already exists, use first admin user as bootstrap admin user ({skipped.email}):")
            logger.info(f"user ID: {skipped.user_id}")
            logger.info(f"role ID: {skipped.role_id}")
            return skipped.user_id


async def bootstrap_models(configuration: Configuration, postgres_session: AsyncSession, bootstrap_admin_user_id: int) -> int:
    router_repository = PostgresRouterRepository(postgres_session=postgres_session, app_title=configuration.settings.app_title)
    provider_repository = PostgresProviderRepository(postgres_session=postgres_session)
    # @TODO: remove after make optional metrics logger and request manager in httpmodelclient
    redis_client = redis.Redis(connection_pool=global_context.redis_pool)
    metrics_logger = ModelMetricsLogger(redis_client=redis_client)
    request_manager = RequestContextManager()
    provider_gateway = ModelProviderGateway(metrics_logger=metrics_logger, request_manager=request_manager)

    result = await BootstrapModelsUseCase(
        router_repository=router_repository,
        provider_repository=provider_repository,
        provider_gateway=provider_gateway,
    ).execute(routers_to_create=configuration.models, bootstrap_admin_user_id=bootstrap_admin_user_id)

    match result:
        case BootstrapModelsUseCaseSuccess() as success:
            logger.info(f"{success.number_of_routers} routers successfully created during bootstrap.")
            return success.number_of_routers
        case BootstrapModelsUseCaseSkipped() as skipped:
            logger.info(f"{skipped.number_of_routers} routers already exist, skipping bootstrap creation.")
            return skipped.number_of_routers
        case RouterNameAlreadyExistsError() as error:
            raise RuntimeError(f"Router name or alias is already taken ({error.name}) by another router.")
        case ProviderAlreadyExistsError() as error:
            raise RuntimeError(f"Provider {error.model_name} already exists ({error.url}) for the same router ({error.router_id}).")
        case ProviderNotReachableError() as error:
            raise RuntimeError(f"Provider {error.model_name} not reachable ({error.status_code}): {error.detail}")
        case InconsistentModelVectorSizeError() as error:
            raise RuntimeError(f"Inconsistent model vector size ({error.router_name}).")
        case InconsistentModelMaxContextLengthError() as error:
            raise RuntimeError(f"Inconsistent model max context length ({error.router_name}).")
        case error:
            return error


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
        raise RuntimeError(f"Vector size is None (no provider for this model {routers[0].name}).")

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
        secret_key=configuration.settings.auth_secret_key,
        key_max_expiration_days=configuration.settings.auth_key_max_expiration_days,
        playground_session_duration=configuration.settings.auth_playground_session_duration,
    )


def create_limiter(configuration: Configuration, redis_pool: redis.ConnectionPool) -> Limiter:
    return Limiter(redis_pool=redis_pool, strategy=configuration.settings.rate_limiting_strategy)


def create_tokenizer(configuration: Configuration) -> UsageTokenizer:
    return UsageTokenizer(tokenizer=configuration.settings.usage_tokenizer)


def initialize_tokenizer(configuration: Configuration) -> Encoding:
    match configuration.settings.usage_tokenizer:
        case Tokenizer.TIKTOKEN_O200K_BASE:
            return tiktoken.get_encoding("o200k_base")
        case Tokenizer.TIKTOKEN_P50K_BASE:
            return tiktoken.get_encoding("p50k_base")
        case Tokenizer.TIKTOKEN_R50K_BASE:
            return tiktoken.get_encoding("r50k_base")
        case Tokenizer.TIKTOKEN_P50K_EDIT:
            return tiktoken.get_encoding("p50k_edit")
        case Tokenizer.TIKTOKEN_CL100K_BASE:
            return tiktoken.get_encoding("cl100k_base")
        case Tokenizer.TIKTOKEN_GPT2:
            return tiktoken.get_encoding("gpt2")


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
