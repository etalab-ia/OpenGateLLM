from collections.abc import AsyncGenerator
from contextvars import ContextVar

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyRepository
from api.infrastructure.model import ModelProviderGateway
from api.infrastructure.postgres import PostgresKeyRepository, PostgresProviderRepository, PostgresRouterRepository, PostgresUserInfoRepository
from api.schemas.core.context import RequestContext
from api.use_cases.admin.providers import CreateProviderUseCase
from api.use_cases.admin.routers import CreateRouterUseCase, DeleteRouterUseCase, GetOneRouterUseCase, GetRoutersUseCase
from api.use_cases.models import GetModelsUseCase
from api.utils.configuration import configuration
from api.utils.context import global_context, request_context


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


def get_request_context() -> ContextVar[RequestContext]:
    return request_context


def _router_repository(session: AsyncSession) -> PostgresRouterRepository:
    return PostgresRouterRepository(postgres_session=session, app_title=configuration.settings.app_title)


def _user_info_repository(session: AsyncSession) -> PostgresUserInfoRepository:
    return PostgresUserInfoRepository(postgres_session=session)


def get_models_use_case(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_context: RequestContext = Depends(get_request_context),
) -> GetModelsUseCase:
    return GetModelsUseCase(
        router_repository=_router_repository(postgres_session),
        user_id=request_context.get().user_id,
        user_info_repository=_user_info_repository(postgres_session),
    )


def create_provider_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> CreateProviderUseCase:
    return CreateProviderUseCase(
        router_repository=_router_repository(postgres_session),
        provider_repository=PostgresProviderRepository(postgres_session=postgres_session),
        provider_gateway=ModelProviderGateway(),
        user_info_repository=_user_info_repository(postgres_session),
    )


def get_one_router_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> GetOneRouterUseCase:
    return GetOneRouterUseCase(
        router_repository=_router_repository(postgres_session),
        user_info_repository=_user_info_repository(postgres_session),
    )


def get_routers_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> GetRoutersUseCase:
    return GetRoutersUseCase(
        router_repository=_router_repository(postgres_session),
        user_info_repository=_user_info_repository(postgres_session),
    )


def create_router_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> CreateRouterUseCase:
    return CreateRouterUseCase(
        router_repository=_router_repository(postgres_session),
        user_info_repository=_user_info_repository(postgres_session),
    )


def delete_router_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> DeleteRouterUseCase:
    return DeleteRouterUseCase(
        router_repository=_router_repository(postgres_session),
        user_info_repository=_user_info_repository(postgres_session),
    )


def get_key_repository(postgres_session: AsyncSession = Depends(get_postgres_session)) -> KeyRepository:
    return PostgresKeyRepository(postgres_session=postgres_session)


def get_master_key() -> str:
    return configuration.settings.auth_master_key
