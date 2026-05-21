from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Any

from fastapi import Depends
import redis.asyncio as redis
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyRepository
from api.domain.provider import ProviderMetricsLogger, ProviderRepository
from api.domain.role import LimitRepository, PermissionRepository
from api.infrastructure.fastapi.context import RequestContextManager
from api.infrastructure.http.model import ModelTokenizerComputer
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
from api.infrastructure.redis import RedisProviderMetricsLogger
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
from api.use_cases.admin.users import CreateUserUseCase, GetOneUserUseCase
from api.use_cases.health import GetHealthModelsUseCase
from api.use_cases.models import GetModelsUseCase, GetModelUseCase
from api.utils.configuration import configuration
from api.utils.context import global_context, request_context


def get_request_context() -> ContextVar[RequestContext]:
    # @TODO: replace with RequestContextManager.get_request_context()
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


def get_key_repository(postgres_session: AsyncSession = Depends(get_postgres_session)) -> KeyRepository:
    return PostgresKeyRepository(postgres_session=postgres_session)


# helpers
def _provider_metrics_logger(redis_client: Redis = Depends(get_redis_client)) -> ProviderMetricsLogger:
    return RedisProviderMetricsLogger(redis_client=redis_client)


def get_tokenizer_computer() -> ModelTokenizerComputer:
    return ModelTokenizerComputer(tokenizer=global_context._tokenizer)


def get_request_manager() -> RequestContextManager:
    return RequestContextManager()


def _provider_gateway(
    provider_metrics_logger: ProviderMetricsLogger = Depends(_provider_metrics_logger),
    request_manager: RequestContextManager = Depends(get_request_manager),
) -> ModelProviderGateway:
    return ModelProviderGateway(provider_metrics_logger=provider_metrics_logger, request_manager=request_manager)


# health use cases
def get_health_models_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: Redis = Depends(get_redis_client),
    request_context: RequestContext = Depends(get_request_context),
) -> GetHealthModelsUseCase:
    return GetHealthModelsUseCase(
        provider_metrics_logger=_provider_metrics_logger(redis_client=redis_client),
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


# users use cases
def create_user_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> CreateUserUseCase:
    return CreateUserUseCase(user_repository=_user_repository(postgres_session), user_with_role_query=_user_with_role_query(postgres_session))


def get_one_user_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetOneUserUseCase:
    return GetOneUserUseCase(user_repository=_user_repository(postgres_session), user_with_role_query=_user_with_role_query(postgres_session))


# roles use cases
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


# routers use cases
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


# providers use cases
def create_provider_use_case_factory(
    provider_gateway: ModelProviderGateway = Depends(_provider_gateway),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_manager: RequestContextManager = Depends(get_request_manager),
) -> CreateProviderUseCase:
    return CreateProviderUseCase(
        router_repository=_router_repository(postgres_session),
        provider_repository=_provider_repository(postgres_session),
        provider_gateway=provider_gateway,
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
