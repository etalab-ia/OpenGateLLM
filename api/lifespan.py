from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from langfuse import Langfuse
from openfga_sdk import ClientConfiguration
from openfga_sdk.client import OpenFgaClient
from openfga_sdk.credentials import CredentialConfiguration, Credentials
from openfga_sdk.models import Store
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
import tiktoken
from tiktoken.core import Encoding

from api.dependencies import get_postgres_session
from api.domain.model.errors import (
    InconsistentModelMaxContextLengthError,
    InconsistentModelQosLimitError,
    InconsistentModelVectorSizeError,
    ModelNotFoundError,
)
from api.domain.provider.errors import ProviderAlreadyExistsError, ProviderInvalidResponseError, ProviderNotReachableError
from api.domain.router.errors import RouterNameAlreadyExistsError
from api.infrastructure.bcrypt import BcryptUserPasswordEncoder
from api.infrastructure.configuration import Configuration, Tokenizer
from api.infrastructure.configuration import Model as ModelConfiguration
from api.infrastructure.context import global_context
from api.infrastructure.http import HttpProviderAdapterBuilder, HttpProviderClient
from api.infrastructure.huggingface import HuggingFaceTokenizerRegistry
from api.infrastructure.openfga import OpenFgaAuthorizationClient, OpenFgaBootstrapAuthorization
from api.infrastructure.postgres import (
    AutocommitSession,
    PostgresLimitRepository,
    PostgresOrganizationRepository,
    PostgresPermissionRepository,
    PostgresProviderRepository,
    PostgresRolesRepository,
    PostgresRouterRepository,
    PostgresUsageRepository,
    PostgresUserRepository,
)
from api.infrastructure.redis import RedisCommandDeniedError, RedisProviderConcurrencyLimiter
from api.use_cases.admin import (
    BootstrapAdminCommand,
    BootstrapAdminUseCase,
    BootstrapAdminUseCaseSkipped,
    BootstrapAdminUseCaseSuccess,
)
from api.use_cases.models import (
    BootstrapModelsCommand,
    BootstrapModelsUseCase,
    BootstrapModelsUseCaseSkipped,
    BootstrapModelsUseCaseSuccess,
    ProviderToCreate,
    RouterToCreate,
)
from api.use_cases.services import ProviderCapabilitiesProbe

logger = logging.getLogger(__name__)

USAGE_SAVES_SHUTDOWN_TIMEOUT_SECONDS = 10


@asynccontextmanager
async def lifespan(app: FastAPI):
    configuration = app.state.configuration

    global_context.redis_pool = await create_redis_pool(configuration)
    await check_redis_permissions(global_context.redis_pool)
    global_context.openfga_client = await create_openfga_client(configuration)
    global_context.postgres_engine = create_postgres_engine(configuration)
    global_context.postgres_session_factory = create_postgres_session_factory(engine=global_context.postgres_engine)
    global_context.autocommit_postgres_session_factory = create_autocommit_postgres_session_factory(engine=global_context.postgres_engine)
    global_context.tokenizer_registry = HuggingFaceTokenizerRegistry()

    async for postgres_session in get_postgres_session():
        bootstrap_admin_user_id = await bootstrap_admin_role_and_user(configuration=configuration, postgres_session=postgres_session)
        if bootstrap_admin_user_id is not None:
            await bootstrap_models(configuration=configuration, postgres_session=postgres_session, bootstrap_admin_user_id=bootstrap_admin_user_id)

    global_context.langfuse = create_langfuse(configuration=configuration)
    global_context.tokenizer = initialize_tokenizer(configuration=configuration)

    yield

    await PostgresUsageRepository.wait_for_pending_saves(timeout=USAGE_SAVES_SHUTDOWN_TIMEOUT_SECONDS)

    if global_context.openfga_client:
        await global_context.openfga_client.close()

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


async def check_redis_permissions(pool: redis.ConnectionPool) -> None:
    async with redis.Redis(connection_pool=pool) as client:
        result = await RedisProviderConcurrencyLimiter(redis_client=client).check_permissions()

    match result:
        case RedisCommandDeniedError() as error:
            logger.error("%s. The API starts without enforcing them.", error.message)
        case None:
            logger.info("Redis allows every command the provider limits need.")


def create_postgres_engine(configuration: Configuration) -> AsyncEngine:
    return create_async_engine(**configuration.dependencies.postgres.model_dump())


def create_postgres_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def create_autocommit_postgres_session_factory(engine: AsyncEngine) -> async_sessionmaker[AutocommitSession]:
    return async_sessionmaker(engine, class_=AutocommitSession, expire_on_commit=False)


async def bootstrap_admin_role_and_user(configuration: Configuration, postgres_session: AsyncSession) -> int | None:
    user_repository = PostgresUserRepository(postgres_session=postgres_session)
    role_repository = PostgresRolesRepository(postgres_session=postgres_session)
    limit_repository = PostgresLimitRepository(postgres_session=postgres_session)
    permission_repository = PostgresPermissionRepository(postgres_session=postgres_session)
    organization_repository = PostgresOrganizationRepository(postgres_session=postgres_session)
    bootstrap_authorization = OpenFgaBootstrapAuthorization(openfga_client=OpenFgaAuthorizationClient(client=global_context.openfga_client))

    result = await BootstrapAdminUseCase(
        user_repository=user_repository,
        role_repository=role_repository,
        limit_repository=limit_repository,
        permission_repository=permission_repository,
        organization_repository=organization_repository,
        user_password_encoder=BcryptUserPasswordEncoder(),
        bootstrap_authorization=bootstrap_authorization,
    ).execute(
        BootstrapAdminCommand(email=configuration.settings.auth_bootsrap_admin_username, password=configuration.settings.auth_bootsrap_admin_password)
    )

    match result:
        case BootstrapAdminUseCaseSuccess() as success:
            logger.info(f"Admin user not found, bootstrap admin created ({success.email}):")
            logger.info(f"user ID: {success.user_id}")
            logger.info(f"role ID: {success.role_id}")
            return success.user_id
        case BootstrapAdminUseCaseSkipped(user_id=None):
            logger.info("Admin bootstrap already handled by another worker, skipping.")
            if postgres_session.in_transaction():
                await postgres_session.rollback()
            return None
        case BootstrapAdminUseCaseSkipped() as skipped:
            logger.info(f"Admin user already exists, use first admin user as bootstrap admin user ({skipped.email}):")
            logger.info(f"user ID: {skipped.user_id}")
            logger.info(f"role ID: {skipped.role_id}")
            return skipped.user_id


async def bootstrap_models(configuration: Configuration, postgres_session: AsyncSession, bootstrap_admin_user_id: int) -> int:
    router_repository = PostgresRouterRepository(postgres_session=postgres_session)
    provider_repository = PostgresProviderRepository(postgres_session=postgres_session)
    provider_capabilities_probe = ProviderCapabilitiesProbe(provider_client=HttpProviderClient(adapter_builder=HttpProviderAdapterBuilder()))

    command = BootstrapModelsCommand(
        routers_to_create=map_models_to_routers_to_create(configuration.models), bootstrap_admin_user_id=bootstrap_admin_user_id
    )

    result = await BootstrapModelsUseCase(
        router_repository=router_repository,
        provider_repository=provider_repository,
        provider_capabilities_probe=provider_capabilities_probe,
    ).execute(command)

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
        case ProviderInvalidResponseError() as error:
            raise RuntimeError(f"Provider {error.model_name} returned an invalid response: {error.detail}")
        case InconsistentModelVectorSizeError() as error:
            raise RuntimeError(f"Inconsistent model vector size ({error.router_name}).")
        case InconsistentModelMaxContextLengthError() as error:
            raise RuntimeError(f"Inconsistent model max context length ({error.router_name}).")
        case InconsistentModelQosLimitError() as error:
            raise RuntimeError(
                f"Inconsistent qos_limit ({error.router_name}): the open providers of a model must all have a qos_limit, or none of them."
            )


def map_models_to_routers_to_create(models: list[ModelConfiguration]) -> list[RouterToCreate]:
    return [
        RouterToCreate(
            name=model.name,
            type=model.type,
            aliases=model.aliases,
            qos_retries_before_reject=model.qos_retries_before_reject,
            cost_prompt_tokens=model.cost_prompt_tokens,
            cost_completion_tokens=model.cost_completion_tokens,
            providers=[
                ProviderToCreate(
                    type=provider.type,
                    url=provider.url,
                    key=provider.key,
                    timeout=provider.timeout,
                    qos_limit=provider.qos_limit,
                    model_name=provider.model_name,
                    model_hosting_zone=provider.model_hosting_zone,
                    model_total_params=provider.model_total_params,
                    model_active_params=provider.model_active_params,
                )
                for provider in model.providers
            ],
        )
        for model in models
    ]


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


def create_langfuse(configuration: Configuration) -> Langfuse | None:
    if configuration.dependencies.langfuse is None:
        return None

    langfuse = Langfuse(**configuration.dependencies.langfuse.model_dump())
    if not langfuse.auth_check():
        logger.warning("Cannot connect to Langfuse. Check your langfuse dependency configuration (public_key, secret_key, url).")
        return None

    return langfuse


async def create_openfga_client(configuration: Configuration) -> OpenFgaClient:
    openfga_config = configuration.dependencies.openfga
    client = OpenFgaClient(
        configuration=ClientConfiguration(
            api_url=openfga_config.url,
            credentials=Credentials(method="api_token", configuration=CredentialConfiguration(api_token=openfga_config.api_token)),
        )
    )

    stores = await list_openfga_stores_by_name(client=client, store_name=openfga_config.store_name)
    if len(stores) != 1:
        await client.close()
        raise RuntimeError(f"Expected one OpenFGA store named '{openfga_config.store_name}', found {len(stores)}.")

    client.set_store_id(stores[0].id)

    latest = await client.read_latest_authorization_model()
    if latest.authorization_model is None:
        await client.close()
        raise RuntimeError(f"OpenFGA store '{openfga_config.store_name}' has no authorization model.")

    client.set_authorization_model_id(latest.authorization_model.id)

    return client


async def list_openfga_stores_by_name(client: OpenFgaClient, store_name: str) -> list[Store]:
    stores: list[Store] = []
    continuation_token: str | None = None
    while True:
        options = {"name": store_name}
        if continuation_token:
            options["continuation_token"] = continuation_token
        response = await client.list_stores(options=options)
        stores.extend(response.stores)
        continuation_token = response.continuation_token
        if not continuation_token:
            return stores
