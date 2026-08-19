from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends
import redis.asyncio as redis
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.auth import AuthSsoSessionValidator
from api.domain.key import KeyEncoder, KeyRepository
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.organization import OrganizationRepository
from api.domain.provider import (
    ProviderAdapterBuilder,
    ProviderClient,
    ProviderLoadBalancer,
    ProviderMetricsLogger,
    ProviderRepository,
)
from api.domain.role import LimitRepository, PermissionRepository
from api.domain.router import RouterRateLimiter
from api.domain.usage import UsageRecorder
from api.domain.user import AuthenticatedUserQuery, UserPasswordEncoder
from api.infrastructure.bcrypt import BcryptUserPasswordEncoder
from api.infrastructure.ecologit import EcologitModelEnvironmentalImpactsComputer
from api.infrastructure.fastapi import RequestContextUsageRecorder
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.http import HttpAuthSsoSessionValidator, HttpProviderAdapterBuilder, HttpProviderClient
from api.infrastructure.jwt import JwtKeyEncoder
from api.infrastructure.postgres import (
    PostgresAuthenticatedUserQuery,
    PostgresKeyRepository,
    PostgresLimitRepository,
    PostgresOrganizationRepository,
    PostgresPermissionRepository,
    PostgresProviderRepository,
    PostgresRolesRepository,
    PostgresRouterRepository,
    PostgresUserRepository,
)
from api.infrastructure.redis import RedisProviderLoadBalancer, RedisProviderMetricsLogger, RedisRouterRateLimiter
from api.infrastructure.tiktoken import TiktokenModelTokenizer
from api.use_cases.admin.keys import CreateKeyUseCase, GetKeysUseCase, GetOneKeyUseCase
from api.use_cases.admin.providers import (
    CreateProviderUseCase,
    DeleteProviderUseCase,
    GetOneProviderUseCase,
    GetProvidersUseCase,
    UpdateProviderUseCase,
)
from api.use_cases.admin.roles import CreateRoleUseCase, DeleteRoleUseCase, GetRolesUseCase, GetRoleUseCase, UpdateRoleUseCase
from api.use_cases.admin.routers import CreateRouterUseCase, DeleteRouterUseCase, GetOneRouterUseCase, GetRoutersUseCase, UpdateRouterUseCase
from api.use_cases.admin.users import CreateUserUseCase, DeleteUserUseCase, GetOneUserUseCase, GetUsersUseCase, UpdateUserUseCase
from api.use_cases.audio import CreateAudioTranscriptionsUseCase
from api.use_cases.auth import AuthLoginUseCase, AuthSsoLoginUseCase
from api.use_cases.embeddings import CreateEmbeddingsUseCase
from api.use_cases.health import GetHealthModelsUseCase
from api.use_cases.models import GetModelsUseCase, GetModelUseCase
from api.use_cases.ocr import CreateOCRUseCase
from api.use_cases.reranks import CreateRerankUseCase
from api.use_cases.services import ProviderCapabilitiesProbe
from api.utils.configuration import configuration
from api.utils.context import global_context


# databases
async def get_postgres_session() -> AsyncGenerator[AsyncSession]:
    session_factory = global_context.postgres_session_factory
    async with session_factory() as postgres_session:
        try:
            yield postgres_session
            if postgres_session.in_transaction():
                await postgres_session.commit()
        except Exception:
            if postgres_session.in_transaction():
                await postgres_session.rollback()
            raise


async def get_redis_client() -> AsyncGenerator[Redis, Any]:
    client = redis.Redis(connection_pool=global_context.redis_pool)
    yield client
    await client.aclose()


# queries
def _authenticated_user_query(session: AsyncSession = Depends(get_postgres_session)) -> AuthenticatedUserQuery:
    return PostgresAuthenticatedUserQuery(postgres_session=session)


# helpers
def _auth_sso_session_validator() -> AuthSsoSessionValidator:
    return HttpAuthSsoSessionValidator(auth_playground_url=configuration.settings.auth_playground_url)


def _key_encoder() -> KeyEncoder:
    return JwtKeyEncoder(secret_key=configuration.settings.auth_secret_key)


def _model_tokenizer() -> ModelTokenizer:
    return TiktokenModelTokenizer(model=global_context._tokenizer)


def _model_environmental_impacts_computer() -> ModelEnvironmentalImpactsComputer:
    return EcologitModelEnvironmentalImpactsComputer()


def _provider_metrics_logger(redis_client: Redis = Depends(get_redis_client)) -> ProviderMetricsLogger:
    return RedisProviderMetricsLogger(redis_client=redis_client)


def _provider_adapter_builder() -> ProviderAdapterBuilder:
    return HttpProviderAdapterBuilder()


def _provider_client() -> ProviderClient:
    return HttpProviderClient()


def _provider_load_balancer(redis_client: Redis = Depends(get_redis_client)) -> ProviderLoadBalancer:
    return RedisProviderLoadBalancer(redis_client=redis_client)


def _provider_capabilities_probe(
    provider_client: ProviderClient = Depends(_provider_client),
    provider_adapter_builder: ProviderAdapterBuilder = Depends(_provider_adapter_builder),
) -> ProviderCapabilitiesProbe:
    return ProviderCapabilitiesProbe(provider_client=provider_client, provider_adapter_builder=provider_adapter_builder)


def _user_password_encoder() -> UserPasswordEncoder:
    return BcryptUserPasswordEncoder()


def _router_rate_limiter() -> RouterRateLimiter:
    return RedisRouterRateLimiter(redis_pool=global_context.redis_pool, strategy=configuration.settings.rate_limiting_strategy)


def _usage_recorder() -> UsageRecorder:
    return RequestContextUsageRecorder(request_context=request_context)


# repositories
def _key_repository(key_encoder: KeyEncoder = Depends(_key_encoder), session: AsyncSession = Depends(get_postgres_session)) -> KeyRepository:
    return PostgresKeyRepository(key_encoder=key_encoder, postgres_session=session)


def _organization_repository(session: AsyncSession) -> OrganizationRepository:
    return PostgresOrganizationRepository(postgres_session=session)


def _user_repository(session: AsyncSession) -> PostgresUserRepository:
    return PostgresUserRepository(postgres_session=session)


def _role_repository(session: AsyncSession) -> PostgresRolesRepository:
    return PostgresRolesRepository(postgres_session=session)


def _router_repository(session: AsyncSession) -> PostgresRouterRepository:
    return PostgresRouterRepository(postgres_session=session, app_title=configuration.settings.app_title)


def _limit_repository(session: AsyncSession) -> LimitRepository:
    return PostgresLimitRepository(postgres_session=session)


def _permission_repository(session: AsyncSession) -> PermissionRepository:
    return PostgresPermissionRepository(postgres_session=session)


def _provider_repository(session: AsyncSession) -> ProviderRepository:
    return PostgresProviderRepository(postgres_session=session)


# audio use cases
def create_audio_transcriptions_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: Redis = Depends(get_redis_client),
    model_environmental_impacts_computer: ModelEnvironmentalImpactsComputer = Depends(_model_environmental_impacts_computer),
    model_tokenizer: ModelTokenizer = Depends(_model_tokenizer),
    provider_adapter_builder: ProviderAdapterBuilder = Depends(_provider_adapter_builder),
    provider_client: ProviderClient = Depends(_provider_client),
) -> CreateAudioTranscriptionsUseCase:
    return CreateAudioTranscriptionsUseCase(
        model_environmental_impacts_computer=model_environmental_impacts_computer,
        model_tokenizer=model_tokenizer,
        provider_adapter_builder=provider_adapter_builder,
        provider_client=provider_client,
        provider_load_balancer=_provider_load_balancer(redis_client),
        provider_metrics_logger=_provider_metrics_logger(redis_client),
        provider_repository=_provider_repository(postgres_session),
        router_rate_limiter=_router_rate_limiter(),
        router_repository=_router_repository(postgres_session),
        usage_recorder=_usage_recorder(),
        audio_file_size_limit=configuration.settings.audio_file_size_limit,
    )


# auth use cases
def auth_login_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    key_encoder: KeyEncoder = Depends(_key_encoder),
    password_encoder: UserPasswordEncoder = Depends(_user_password_encoder),
) -> AuthLoginUseCase:
    return AuthLoginUseCase(
        key_repository=PostgresKeyRepository(key_encoder=key_encoder, postgres_session=postgres_session),
        user_repository=PostgresUserRepository(postgres_session=postgres_session),
        user_password_encoder=password_encoder,
        auth_login_type=configuration.settings.auth_login_type,
        auth_login_session_duration=configuration.settings.auth_login_session_duration,
    )


def auth_sso_login_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    key_encoder: KeyEncoder = Depends(_key_encoder),
) -> AuthSsoLoginUseCase:
    return AuthSsoLoginUseCase(
        key_repository=_key_repository(key_encoder=key_encoder, session=postgres_session),
        organization_repository=_organization_repository(session=postgres_session),
        user_repository=_user_repository(session=postgres_session),
        role_repository=_role_repository(session=postgres_session),
        auth_sso_session_validator=_auth_sso_session_validator(),
        auth_login_type=configuration.settings.auth_login_type,
        auth_sso_default_role_id=configuration.settings.auth_sso_default_role_id,
        auth_sso_default_organization_id=configuration.settings.auth_sso_default_organization_id,
    )


# health use cases
def get_health_models_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    provider_adapter_builder: ProviderAdapterBuilder = Depends(_provider_adapter_builder),
    provider_client: ProviderClient = Depends(_provider_client),
    redis_client: Redis = Depends(get_redis_client),
) -> GetHealthModelsUseCase:
    return GetHealthModelsUseCase(
        provider_adapter_builder=provider_adapter_builder,
        provider_client=provider_client,
        provider_metrics_logger=_provider_metrics_logger(redis_client),
        router_repository=_router_repository(postgres_session),
        provider_repository=_provider_repository(postgres_session),
    )


# embeddings use cases
def create_embeddings_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: Redis = Depends(get_redis_client),
    model_environmental_impacts_computer: ModelEnvironmentalImpactsComputer = Depends(_model_environmental_impacts_computer),
    model_tokenizer: ModelTokenizer = Depends(_model_tokenizer),
    provider_adapter_builder: ProviderAdapterBuilder = Depends(_provider_adapter_builder),
    provider_client: ProviderClient = Depends(_provider_client),
) -> CreateEmbeddingsUseCase:
    return CreateEmbeddingsUseCase(
        model_environmental_impacts_computer=model_environmental_impacts_computer,
        model_tokenizer=model_tokenizer,
        provider_adapter_builder=provider_adapter_builder,
        provider_client=provider_client,
        provider_load_balancer=_provider_load_balancer(redis_client),
        provider_metrics_logger=_provider_metrics_logger(redis_client),
        provider_repository=_provider_repository(postgres_session),
        router_rate_limiter=_router_rate_limiter(),
        router_repository=_router_repository(postgres_session),
        usage_recorder=_usage_recorder(),
    )


# keys use cases
def create_key_use_case_factory(key_repository: KeyRepository = Depends(_key_repository)) -> CreateKeyUseCase:
    return CreateKeyUseCase(key_repository=key_repository)


def get_keys_use_case_factory(key_repository: KeyRepository = Depends(_key_repository)) -> GetKeysUseCase:
    return GetKeysUseCase(key_repository=key_repository)


def get_one_key_use_case_factory(key_repository: KeyRepository = Depends(_key_repository)) -> GetOneKeyUseCase:
    return GetOneKeyUseCase(key_repository=key_repository)


# models use cases
def get_models_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetModelsUseCase:
    return GetModelsUseCase(router_repository=_router_repository(postgres_session))


def get_model_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetModelUseCase:
    return GetModelUseCase(router_repository=_router_repository(postgres_session))


# ocr use cases
def create_ocr_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: Redis = Depends(get_redis_client),
    model_environmental_impacts_computer: ModelEnvironmentalImpactsComputer = Depends(_model_environmental_impacts_computer),
    model_tokenizer: ModelTokenizer = Depends(_model_tokenizer),
    provider_adapter_builder: ProviderAdapterBuilder = Depends(_provider_adapter_builder),
    provider_client: ProviderClient = Depends(_provider_client),
) -> CreateOCRUseCase:
    return CreateOCRUseCase(
        model_environmental_impacts_computer=model_environmental_impacts_computer,
        model_tokenizer=model_tokenizer,
        provider_adapter_builder=provider_adapter_builder,
        provider_client=provider_client,
        provider_load_balancer=_provider_load_balancer(redis_client),
        provider_metrics_logger=_provider_metrics_logger(redis_client),
        provider_repository=_provider_repository(postgres_session),
        router_rate_limiter=_router_rate_limiter(),
        router_repository=_router_repository(postgres_session),
        usage_recorder=_usage_recorder(),
    )


# user use cases
def create_user_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> CreateUserUseCase:
    return CreateUserUseCase(user_repository=_user_repository(postgres_session), user_password_encoder=_user_password_encoder())


def get_one_user_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetOneUserUseCase:
    return GetOneUserUseCase(user_repository=_user_repository(postgres_session))


def get_users_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetUsersUseCase:
    return GetUsersUseCase(user_repository=_user_repository(postgres_session))


def delete_user_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> DeleteUserUseCase:
    return DeleteUserUseCase(
        user_repository=_user_repository(postgres_session),
        router_repository=_router_repository(postgres_session),
        provider_repository=_provider_repository(postgres_session),
    )


def update_user_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> UpdateUserUseCase:
    return UpdateUserUseCase(user_repository=_user_repository(postgres_session), user_password_encoder=_user_password_encoder())


# rerank use cases
def create_rerank_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: Redis = Depends(get_redis_client),
    model_environmental_impacts_computer: ModelEnvironmentalImpactsComputer = Depends(_model_environmental_impacts_computer),
    model_tokenizer: ModelTokenizer = Depends(_model_tokenizer),
    provider_adapter_builder: ProviderAdapterBuilder = Depends(_provider_adapter_builder),
    provider_client: ProviderClient = Depends(_provider_client),
) -> CreateRerankUseCase:
    return CreateRerankUseCase(
        model_environmental_impacts_computer=model_environmental_impacts_computer,
        model_tokenizer=model_tokenizer,
        provider_adapter_builder=provider_adapter_builder,
        provider_client=provider_client,
        provider_load_balancer=_provider_load_balancer(redis_client),
        provider_metrics_logger=_provider_metrics_logger(redis_client),
        provider_repository=_provider_repository(postgres_session),
        router_rate_limiter=_router_rate_limiter(),
        router_repository=_router_repository(postgres_session),
        usage_recorder=_usage_recorder(),
    )


# roles use cases
def create_role_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> CreateRoleUseCase:
    return CreateRoleUseCase(
        role_repository=_role_repository(postgres_session),
        limit_repository=_limit_repository(postgres_session),
        permission_repository=_permission_repository(postgres_session),
    )


def update_role_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> UpdateRoleUseCase:
    return UpdateRoleUseCase(
        role_repository=_role_repository(postgres_session),
        limit_repository=_limit_repository(postgres_session),
        permission_repository=_permission_repository(postgres_session),
    )


def get_roles_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetRolesUseCase:
    return GetRolesUseCase(
        role_repository=_role_repository(postgres_session),
        limit_repository=_limit_repository(postgres_session),
        permission_repository=_permission_repository(postgres_session),
    )


def get_role_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetRoleUseCase:
    return GetRoleUseCase(
        role_repository=_role_repository(postgres_session),
    )


def delete_role_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> DeleteRoleUseCase:
    return DeleteRoleUseCase(
        role_repository=_role_repository(postgres_session),
    )


# router use cases
def get_one_router_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetOneRouterUseCase:
    return GetOneRouterUseCase(
        router_repository=_router_repository(postgres_session),
    )


def get_routers_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetRoutersUseCase:
    return GetRoutersUseCase(
        router_repository=_router_repository(postgres_session),
    )


def create_router_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> CreateRouterUseCase:
    return CreateRouterUseCase(
        router_repository=_router_repository(postgres_session),
    )


def delete_router_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> DeleteRouterUseCase:
    return DeleteRouterUseCase(
        router_repository=_router_repository(postgres_session),
    )


def update_router_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> UpdateRouterUseCase:
    return UpdateRouterUseCase(
        router_repository=_router_repository(postgres_session),
    )


# provider use cases
def create_provider_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    provider_capabilities_probe: ProviderCapabilitiesProbe = Depends(_provider_capabilities_probe),
) -> CreateProviderUseCase:
    return CreateProviderUseCase(
        router_repository=_router_repository(postgres_session),
        provider_repository=_provider_repository(postgres_session),
        provider_capabilities_probe=provider_capabilities_probe,
    )


def update_provider_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> UpdateProviderUseCase:
    return UpdateProviderUseCase(
        router_repository=_router_repository(postgres_session),
        provider_repository=_provider_repository(postgres_session),
    )


def delete_provider_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> DeleteProviderUseCase:
    return DeleteProviderUseCase(
        provider_repository=_provider_repository(postgres_session),
    )


def get_one_provider_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetOneProviderUseCase:
    return GetOneProviderUseCase(
        provider_repository=_provider_repository(postgres_session),
    )


def get_providers_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetProvidersUseCase:
    return GetProvidersUseCase(
        provider_repository=_provider_repository(postgres_session),
    )
