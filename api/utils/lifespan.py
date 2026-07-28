from contextlib import asynccontextmanager

from fastapi import FastAPI
from langfuse import Langfuse
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
import tiktoken
from tiktoken.core import Encoding

from api.dependencies import get_postgres_session
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError, ModelNotFoundError
from api.domain.provider.errors import ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router.errors import RouterNameAlreadyExistsError
from api.helpers._identityaccessmanager import IdentityAccessManager
from api.helpers._langfusemanager import LangfuseManager
from api.helpers._limiter import Limiter
from api.helpers._usagemanager import UsageManager
from api.helpers._usagetokenizer import UsageTokenizer
from api.helpers.models import ModelRegistry
from api.infrastructure.bcrypt import BcryptUserPasswordEncoder
from api.infrastructure.http import HttpProviderAdapterBuilder, HttpProviderClient
from api.infrastructure.postgres import (
    PostgresLimitRepository,
    PostgresPermissionRepository,
    PostgresProviderRepository,
    PostgresRolesRepository,
    PostgresRouterRepository,
    PostgresUserRepository,
)
from api.schemas.core.configuration import Configuration, Tokenizer
from api.use_cases.admin import (
    BootstrapAdminCommand,
    BootstrapAdminUseCase,
    BootstrapAdminUseCaseSkipped,
    BootstrapAdminUseCaseSuccess,
)
from api.use_cases.models import BootstrapModelsUseCase, BootstrapModelsUseCaseSkipped, BootstrapModelsUseCaseSuccess
from api.use_cases.services import ProviderCapabilitiesProbe
from api.utils.configuration import get_configuration
from api.utils.context import global_context
from api.utils.logging import init_logger

logger = init_logger(name=__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configuration = get_configuration()

    global_context.redis_pool = await create_redis_pool(configuration)
    global_context.postgres_engine, global_context.postgres_session_factory = create_postgres_session_factory(configuration)

    async for postgres_session in get_postgres_session():
        bootstrap_admin_user_id = await bootstrap_admin_role_and_user(configuration=configuration, postgres_session=postgres_session)
        await bootstrap_models(configuration=configuration, postgres_session=postgres_session, bootstrap_admin_user_id=bootstrap_admin_user_id)

    global_context.model_registry = await create_model_registry(configuration, global_context.postgres_session_factory)
    global_context.usage_manager = create_usage_manager()

    global_context.langfuse_client = create_langfuse_client(configuration=configuration)
    global_context.identity_access_manager = create_identity_access_manager(configuration=configuration)
    global_context.limiter = create_limiter(configuration=configuration, redis_pool=global_context.redis_pool)
    global_context.tokenizer = create_tokenizer(configuration=configuration)
    global_context._tokenizer = initialize_tokenizer(configuration=configuration)

    await global_context.limiter.reset()

    yield

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
        user_password_encoder=BcryptUserPasswordEncoder(),
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
    provider_capabilities_probe = ProviderCapabilitiesProbe(
        provider_client=HttpProviderClient(),
        provider_adapter_builder=HttpProviderAdapterBuilder(),
    )

    result = await BootstrapModelsUseCase(
        router_repository=router_repository,
        provider_repository=provider_repository,
        provider_capabilities_probe=provider_capabilities_probe,
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
        case ModelNotFoundError() as error:
            raise RuntimeError(f"Provider {error.name} are not found.")
        case ProviderAlreadyExistsError() as error:
            raise RuntimeError(f"Provider {error.model_name} already exists ({error.url}) for the same router ({error.router_id}).")
        case ProviderNotReachableError() as error:
            raise RuntimeError(f"Provider {error.model_name} not reachable ({error.status_code}): {error.detail}")
        case InconsistentModelVectorSizeError() as error:
            raise RuntimeError(f"Inconsistent model vector size ({error.router_name}).")
        case InconsistentModelMaxContextLengthError() as error:
            raise RuntimeError(f"Inconsistent model max context length ({error.router_name}).")


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


def create_usage_manager() -> UsageManager:
    return UsageManager()


def create_identity_access_manager(configuration: Configuration) -> IdentityAccessManager:
    return IdentityAccessManager(
        secret_key=configuration.settings.auth_secret_key,
        key_max_expiration_days=configuration.settings.auth_key_max_expiration_days,
        playground_session_duration=configuration.settings.auth_login_session_duration,
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


def create_langfuse_client(configuration: Configuration) -> LangfuseManager | None:
    if configuration.dependencies.langfuse is None:
        return None

    langfuse_client = Langfuse(**configuration.dependencies.langfuse.model_dump())
    if not langfuse_client.auth_check():
        logger.warning("Cannot connect to Langfuse. Check your langfuse dependency configuration (public_key, secret_key, url).")
        return None

    return LangfuseManager(client=langfuse_client)
