from contextvars import ContextVar

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyRepository
from api.infrastructure.postgres import PostgresKeyRepository, PostgresRouterRepository, PostgresUserInfoRepository
from api.schemas.core.context import RequestContext
from api.use_cases.models import GetModelsUseCase
from api.utils.configuration import configuration
from api.utils.context import global_context, request_context


async def get_postgres_session() -> AsyncSession:
    """
    Get a PostgreSQL postgres_session from the global context.

    Returns:
        AsyncSession: A PostgreSQL postgres_session instance.
    """

    session_factory = global_context.postgres_session_factory
    async with session_factory() as postgres_session:
        yield postgres_session

        if postgres_session.in_transaction():
            await postgres_session.close()


def get_request_context() -> ContextVar[RequestContext]:
    """
    Get the RequestContext ContextVar from the global context.

    Returns:
        ContextVar[RequestContext]: The RequestContext ContextVar instance.
    """

    return request_context


def get_models_use_case(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_context: RequestContext = Depends(get_request_context),
) -> GetModelsUseCase:
    return GetModelsUseCase(
        router_repository=PostgresRouterRepository(postgres_session=postgres_session, app_title=configuration.settings.app_title),
        user_id=request_context.get().user_id,
        user_info_repository=PostgresUserInfoRepository(postgres_session=postgres_session),
    )


def get_key_repository(postgres_session: AsyncSession = Depends(get_postgres_session)) -> KeyRepository:
    return PostgresKeyRepository(postgres_session=postgres_session)


def get_master_key() -> str:
    return configuration.settings.auth_master_key
