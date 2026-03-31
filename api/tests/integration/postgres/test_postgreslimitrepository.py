import pytest

from api.domain.role.entities import Limit, LimitType
from api.infrastructure.postgres._postgreslimitrepository import PostgresLimitRepository
from api.tests.integration.factories import LimitSQLFactory, RoleSQLFactory, RouterSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresLimitRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestCreateLimits:
    async def test_returns_empty_list_when_limits_is_empty(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_limits(role_id=role.id, limits=[])

        # Assert
        assert result == []

    async def test_creates_multiple_limits_and_returns_them(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        router_1 = RouterSQLFactory()
        router_2 = RouterSQLFactory()
        await db_session.flush()
        limits = [
            Limit(router=router_1.id, type=LimitType.TPM, value=100),
            Limit(router=router_2.id, type=LimitType.RPM, value=200),
        ]

        # Act
        result = await repository.create_limits(role_id=role.id, limits=limits)

        # Assert
        assert len(result) == 2
        result_by_router = {r.router: r for r in result}
        assert result_by_router[router_1.id].type == LimitType.TPM
        assert result_by_router[router_1.id].value == 100
        assert result_by_router[router_2.id].type == LimitType.RPM
        assert result_by_router[router_2.id].value == 200

    async def test_limit_value_can_be_none(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        router = RouterSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_limits(role_id=role.id, limits=[Limit(router=router.id, type=LimitType.TPD, value=None)])

        # Assert
        assert result[0].value is None

    async def test_should_create_only_none_duplicate_permission(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        router = RouterSQLFactory()
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=100)
        await db_session.flush()

        # Act
        limits = await repository.create_limits(
            role_id=role.id, limits=[Limit(router=router.id, type=LimitType.TPM, value=200), Limit(router=router.id, type=LimitType.RPM, value=200)]
        )

        # Assert
        assert limits == [Limit(router=router.id, type=LimitType.RPM, value=200)]
