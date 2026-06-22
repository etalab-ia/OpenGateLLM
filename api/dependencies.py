from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Any

from fastapi import Depends
import redis.asyncio as redis
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.auth import AuthOidcProviderCache, AuthOidcProviderClient, AuthOidcTokenValidator
from api.domain.key import KeyEncoder, KeyRepository
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.provider import (
    ProviderAdapterBuilder,
    ProviderClient,
    ProviderGateway,
    ProviderLoadBalancer,
    ProviderMetricsLogger,
    ProviderRepository,
)
from api.domain.role import LimitRepository, PermissionRepository
from api.domain.router import RouterRateLimiter
from api.domain.user import UserPasswordEncoder
from api.infrastructure.bcrypt import BcryptUserPasswordEncoder
from api.infrastructure.ecologit import EcologitModelEnvironmentalImpactsComputer
from api.infrastructure.fastapi.context import request_context
from api.infrastructure.http import HttpAuthOidcProviderClient, HttpProviderAdapterBuilder, HttpProviderClient
from api.infrastructure.jwt import JwtAuthOidcTokenValidator, JwtKeyEncoder
from api.infrastructure.model import ModelProviderGateway
from api.infrastructure.postgres import (
    PostgresAuthenticatedUserQuery,
    PostgresKeyRepository,
    PostgresLimitRepository,
    PostgresPermissionRepository,
    PostgresProviderRepository,
    PostgresRolesRepository,
    PostgresRouterRepository,
    PostgresUserRepository,
)
from api.infrastructure.redis import RedisAuthOidcProviderCache, RedisProviderLoadBalancer, RedisProviderMetricsLogger, RedisRouterRateLimiter
from api.infrastructure.tiktoken import TiktokenModelTokenizer
from api.schemas.core.context import RequestContext
from api.use_cases.admin.keys import CreateKeyUseCase
from api.use_cases.admin.providers import (
    CreateProviderUseCase,
    DeleteProviderUseCase,
    GetOneProviderUseCase,
    GetProvidersUseCase,
    UpdateProviderUseCase,
)
from api.use_cases.admin.roles import CreateRoleUseCase, DeleteRoleUseCase, GetRolesUseCase, GetRoleUseCase, UpdateRoleUseCase
from api.use_cases.admin.routers import CreateRouterUseCase, DeleteRouterUseCase, GetOneRouterUseCase, GetRoutersUseCase, UpdateRouterUseCase
from api.use_cases.admin.users import CreateUserUseCase, DeleteUserUseCase, GetOneUserUseCase, GetUsersUseCase
from api.use_cases.auth import AuthLoginUseCase, AuthOidcLoginUseCase
from api.use_cases.health import GetHealthModelsUseCase
from api.use_cases.models import GetModelsUseCase, GetModelUseCase
from api.use_cases.reranks import CreateRerankUseCase
from api.utils.configuration import configuration
from api.utils.context import global_context


def get_request_context() -> ContextVar[RequestContext]:
    return request_context


def get_secret_key() -> str:
    return configuration.settings.auth_secret_key


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
def _authenticated_user_query(session: AsyncSession = Depends(get_postgres_session)) -> PostgresAuthenticatedUserQuery:
    return PostgresAuthenticatedUserQuery(postgres_session=session)


# helpers
def _auth_oidc_provider_client() -> AuthOidcProviderClient:
    return HttpAuthOidcProviderClient(issuer_url=configuration.settings.auth_sso_oidc_issuer_url)


def _auth_oidc_token_validator() -> AuthOidcTokenValidator:
    return JwtAuthOidcTokenValidator()


def _auth_oidc_provider_cache(redis_client: Redis = Depends(get_redis_client)) -> AuthOidcProviderCache:
    return RedisAuthOidcProviderCache(redis_client=redis_client)


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


def _provider_gateway(
    provider_client: ProviderClient = Depends(_provider_client),
    provider_adapter_builder: ProviderAdapterBuilder = Depends(_provider_adapter_builder),
) -> ProviderGateway:
    return ModelProviderGateway(provider_client=provider_client, provider_adapter_builder=provider_adapter_builder)


def _provider_load_balancer(redis_client: Redis = Depends(get_redis_client)) -> ProviderLoadBalancer:
    return RedisProviderLoadBalancer(redis_client=redis_client)


def _user_password_encoder() -> UserPasswordEncoder:
    return BcryptUserPasswordEncoder()


def _router_rate_limiter() -> RouterRateLimiter:
    return RedisRouterRateLimiter(redis_pool=global_context.redis_pool, strategy=configuration.settings.rate_limiting_strategy)


# repositories
def _key_repository(key_encoder: KeyEncoder = Depends(_key_encoder), session: AsyncSession = Depends(get_postgres_session)) -> KeyRepository:
    return PostgresKeyRepository(key_encoder=key_encoder, postgres_session=session)


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
        login_session_duration=configuration.settings.auth_login_session_duration,
    )


def auth_oidc_login_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    key_encoder: KeyEncoder = Depends(_key_encoder),
    auth_oidc_provider_cache: AuthOidcProviderCache = Depends(_auth_oidc_provider_cache),
) -> AuthOidcLoginUseCase:
    return AuthOidcLoginUseCase(
        key_repository=PostgresKeyRepository(key_encoder=key_encoder, postgres_session=postgres_session),
        user_repository=PostgresUserRepository(postgres_session=postgres_session),
        auth_oidc_provider_client=_auth_oidc_provider_client(),
        auth_oidc_token_validator=_auth_oidc_token_validator(),
        auth_oidc_provider_cache=auth_oidc_provider_cache,
        auth_login_type=configuration.settings.auth_login_type,
        auth_sso_oidc_issuer_url=configuration.settings.auth_sso_oidc_issuer_url,
        auth_sso_client_id=configuration.settings.auth_sso_client_id,
        auth_sso_default_role_id=configuration.settings.auth_sso_default_role_id,
        auth_login_session_duration=configuration.settings.auth_login_session_duration,
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


# keys use cases
def create_key_use_case_factory(key_repository: KeyRepository = Depends(_key_repository)) -> CreateKeyUseCase:
    return CreateKeyUseCase(key_repository=key_repository)


# models use cases
def get_models_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetModelsUseCase:
    return GetModelsUseCase(router_repository=_router_repository(postgres_session))


def get_model_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetModelUseCase:
    return GetModelUseCase(router_repository=_router_repository(postgres_session))


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
    provider_client: ProviderClient = Depends(_provider_client),
) -> CreateProviderUseCase:
    return CreateProviderUseCase(
        router_repository=_router_repository(postgres_session),
        provider_repository=_provider_repository(postgres_session),
        provider_gateway=_provider_gateway(provider_client=provider_client, provider_adapter_builder=HttpProviderAdapterBuilder()),
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
