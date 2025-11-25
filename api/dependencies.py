from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.infrastructure import PostgresRouterRepository, PostgresUserInfoRepository
from api.use_cases.models import GetModelsUseCase
from api.utils.context import global_context


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


def get_models_use_case(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetModelsUseCase:
    return GetModelsUseCase(
        router_repository=PostgresRouterRepository(postgres_session=postgres_session),
        user_info_repository=PostgresUserInfoRepository(postgres_session=postgres_session),
    )
