import pytest
import pytest_asyncio
from sqlalchemy import text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.infrastructure.postgres import PostgresRouterRepository
from api.infrastructure.postgres.models import Base
from api.infrastructure.postgres.models import Provider as ProviderTable
from api.tests.integration.factories.sql import ProviderSQLFactory, RouterSQLFactory, UserSQLFactory
from api.tests.integration.postgresfixtures import bind_sql_factories


# two transactions are needed, which db_session cannot give: these tests commit, so they empty the tables themselves
@pytest_asyncio.fixture(loop_scope="session")
async def session_factory(test_postgres_engine):
    try:
        yield async_sessionmaker(test_postgres_engine, class_=AsyncSession, expire_on_commit=False)
    finally:
        table_list = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        async with test_postgres_engine.begin() as connection:
            await connection.execute(text(f"TRUNCATE {table_list} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture(loop_scope="session")
async def committed_router(session_factory):
    async with session_factory() as session:
        with bind_sql_factories(session):
            router = RouterSQLFactory(user=UserSQLFactory(admin_user=True))
            await session.commit()
    return router


@pytest_asyncio.fixture(loop_scope="session")
async def committed_provider(session_factory):
    async with session_factory() as session:
        with bind_sql_factories(session):
            provider = ProviderSQLFactory(qos_limit=10)
            await session.commit()
    return provider


@pytest.mark.asyncio(loop_scope="session")
class TestLockAndGetRouterById:
    async def test_should_refuse_a_second_lock_on_the_router_until_the_first_transaction_ends(self, session_factory, committed_router):
        async with session_factory() as first_session, session_factory() as second_session:
            # Arrange
            await PostgresRouterRepository(first_session).lock_and_get_router_by_id(committed_router.id)
            await second_session.execute(text("SET LOCAL lock_timeout = '50ms'"))

            # Act & Assert
            with pytest.raises(DBAPIError, match="lock timeout"):
                await PostgresRouterRepository(second_session).lock_and_get_router_by_id(committed_router.id)

    async def test_should_return_the_committed_limit_when_the_session_still_holds_the_former_one(self, session_factory, committed_provider):
        async with session_factory() as session:
            # Arrange
            held_provider = await session.get(ProviderTable, committed_provider.id)
            async with session_factory() as other_session:
                await other_session.execute(update(ProviderTable).where(ProviderTable.id == committed_provider.id).values(qos_limit=20))
                await other_session.commit()

            # Act
            result = await PostgresRouterRepository(session).lock_and_get_router_by_id(committed_provider.router_id)

        # Assert
        assert [provider.qos_limit for provider in result.providers] == [20]
        assert held_provider.qos_limit == 20
