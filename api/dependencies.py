from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Any

from fastapi import Depends
import redis.asyncio as redis
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyRepository
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.provider import ProviderClient, ProviderGateway, ProviderLoadBalancer, ProviderMetricsLogger, ProviderRepository
from api.domain.role import LimitRepository, PermissionRepository
from api.domain.router import RouterRateLimiter
from api.infrastructure.ecologit import EcologitModelEnvironmentalImpactsComputer
from api.infrastructure.http import HttpProviderClient
from api.infrastructure.model import ModelProviderGateway
from api.infrastructure.postgres import (
    PostgresKeyRepository,
    PostgresLimitRepository,
    PostgresPermissionRepository,
    PostgresProviderRepository,
    PostgresRolesRepository,
    PostgresRouterRepository,
    PostgresUserRepository,
    PostgresUserWithRoleQuery,
)
from api.infrastructure.redis import RedisProviderLoadBalancer, RedisProviderMetricsLogger, RedisRouterRateLimiter
from api.infrastructure.tiktoken import TiktokenModelTokenizer
from api.schemas.core.context import RequestContext
from api.use_cases.admin.providers import (
    CreateProviderUseCase,
    DeleteProviderUseCase,
    GetOneProviderUseCase,
    GetProvidersUseCase,
    UpdateProviderUseCase,
)
from api.use_cases.admin.roles import CreateRoleUseCase, DeleteRoleUseCase, GetRolesUseCase, GetRoleUseCase, UpdateRoleUseCase
from api.use_cases.admin.routers import CreateRouterUseCase, DeleteRouterUseCase, GetOneRouterUseCase, GetRoutersUseCase, UpdateRouterUseCase
from api.use_cases.admin.users import CreateUserUseCase, GetOneUserUseCase, GetUsersUseCase
from api.use_cases.health import GetHealthModelsUseCase
from api.use_cases.models import GetModelsUseCase, GetModelUseCase
from api.use_cases.reranks import CreateRerankUseCase
from api.utils.configuration import configuration
from api.utils.context import global_context, request_context


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
def _user_with_role_query(session: AsyncSession) -> PostgresUserWithRoleQuery:
    return PostgresUserWithRoleQuery(postgres_session=session)


# repositories
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


def _key_repository(session: AsyncSession = Depends(get_postgres_session)) -> KeyRepository:
    return PostgresKeyRepository(postgres_session=session)


# helpers
def _model_tokenizer() -> ModelTokenizer:
    return TiktokenModelTokenizer(model=global_context._tokenizer)


def _model_environmental_impacts_computer() -> ModelEnvironmentalImpactsComputer:
    return EcologitModelEnvironmentalImpactsComputer()


def _provider_metrics_logger(redis_client: Redis = Depends(get_redis_client)) -> ProviderMetricsLogger:
    return RedisProviderMetricsLogger(redis_client=redis_client)


def _provider_client() -> ProviderClient:
    return HttpProviderClient()


# TODO: delete model provider gateway class
def _provider_gateway(provider_client: ProviderClient = Depends(_provider_client)) -> ProviderGateway:
    return ModelProviderGateway(provider_client=provider_client)


def _provider_load_balancer(redis_client: Redis = Depends(get_redis_client)) -> ProviderLoadBalancer:
    return RedisProviderLoadBalancer(redis_client=redis_client)


def _router_rate_limiter() -> RouterRateLimiter:
    return RedisRouterRateLimiter(redis_pool=global_context.redis_pool, strategy=configuration.settings.rate_limiting_strategy)


# health use cases
def get_health_models_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: Redis = Depends(get_redis_client),
) -> GetHealthModelsUseCase:
    return GetHealthModelsUseCase(
        provider_metrics_logger=_provider_metrics_logger(redis_client),
        router_repository=_router_repository(postgres_session),
        provider_repository=_provider_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


# models use cases
def get_models_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetModelsUseCase:
    return GetModelsUseCase(
        router_repository=_router_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


def get_model_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetModelUseCase:
    return GetModelUseCase(
        router_repository=_router_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


# user use cases
def create_user_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> CreateUserUseCase:
    return CreateUserUseCase(
        user_repository=_user_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


def get_one_user_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetOneUserUseCase:
    return GetOneUserUseCase(user_repository=_user_repository(postgres_session), user_with_role_query=_user_with_role_query(postgres_session))


def get_users_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetUsersUseCase:
    return GetUsersUseCase(user_repository=_user_repository(postgres_session), user_with_role_query=_user_with_role_query(postgres_session))


# rerank use cases
def create_rerank_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: Redis = Depends(get_redis_client),
) -> CreateRerankUseCase:
    return CreateRerankUseCase(
        model_environmental_impacts_computer=_model_environmental_impacts_computer(),
        model_tokenizer=_model_tokenizer(),
        provider_client=_provider_client(),
        provider_load_balancer=_provider_load_balancer(redis_client),
        provider_metrics_logger=_provider_metrics_logger(redis_client),
        provider_repository=_provider_repository(postgres_session),
        router_rate_limiter=_router_rate_limiter(),
        router_repository=_router_repository(postgres_session),
        user_with_role_query=_user_with_role_query(session=postgres_session),
    )


# role use cases
def create_role_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> CreateRoleUseCase:
    return CreateRoleUseCase(
        role_repository=_role_repository(postgres_session),
        limit_repository=_limit_repository(postgres_session),
        permission_repository=_permission_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


def update_role_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> UpdateRoleUseCase:
    return UpdateRoleUseCase(
        role_repository=_role_repository(postgres_session),
        limit_repository=_limit_repository(postgres_session),
        permission_repository=_permission_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


def get_roles_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetRolesUseCase:
    return GetRolesUseCase(
        role_repository=_role_repository(postgres_session),
        limit_repository=_limit_repository(postgres_session),
        permission_repository=_permission_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


def get_role_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetRoleUseCase:
    return GetRoleUseCase(
        role_repository=_role_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


def delete_role_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> DeleteRoleUseCase:
    return DeleteRoleUseCase(
        role_repository=_role_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


# router use cases
def get_one_router_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetOneRouterUseCase:
    return GetOneRouterUseCase(router_repository=_router_repository(postgres_session), user_with_role_query=_user_with_role_query(postgres_session))


def get_routers_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetRoutersUseCase:
    return GetRoutersUseCase(router_repository=_router_repository(postgres_session), user_with_role_query=_user_with_role_query(postgres_session))


def create_router_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> CreateRouterUseCase:
    return CreateRouterUseCase(router_repository=_router_repository(postgres_session), user_with_role_query=_user_with_role_query(postgres_session))


def delete_router_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> DeleteRouterUseCase:
    return DeleteRouterUseCase(router_repository=_router_repository(postgres_session), user_with_role_query=_user_with_role_query(postgres_session))


def update_router_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> UpdateRouterUseCase:
    return UpdateRouterUseCase(router_repository=_router_repository(postgres_session), user_with_role_query=_user_with_role_query(postgres_session))


# provider use cases
def create_provider_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> CreateProviderUseCase:
    return CreateProviderUseCase(
        router_repository=_router_repository(postgres_session),
        provider_repository=_provider_repository(postgres_session),
        provider_gateway=_provider_gateway(),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


def update_provider_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> UpdateProviderUseCase:
    return UpdateProviderUseCase(
        router_repository=_router_repository(postgres_session),
        provider_repository=_provider_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


def delete_provider_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> DeleteProviderUseCase:
    return DeleteProviderUseCase(
        provider_repository=_provider_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


def get_one_provider_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetOneProviderUseCase:
    return GetOneProviderUseCase(
        provider_repository=_provider_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )


def get_providers_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetProvidersUseCase:
    return GetProvidersUseCase(
        provider_repository=_provider_repository(postgres_session),
        user_with_role_query=_user_with_role_query(postgres_session),
    )
