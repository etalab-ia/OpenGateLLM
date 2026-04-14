import pytest

from api.domain.role.entities import LimitType, PermissionType, Role
from api.domain.role.errors import RoleNotFoundError
from api.infrastructure.postgres import PostgresRolesRepository
from api.tests.integration.factories import LimitSQLFactory, PermissionSQLFactory, RoleSQLFactory, RouterSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresRolesRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetRoleById:
    async def test_returns_role_when_it_exists(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory(name="existing-role")
        await db_session.flush()

        # Act
        result = await repository.get_role_by_id(role_id=role.id)

        # Assert
        assert isinstance(result, Role)
        assert result.id == role.id
        assert result.name == "existing-role"

    async def test_should_return_role_not_found_when_role_does_not_exist(self, repository, db_session):
        # Act & Assert
        result = await repository.get_role_by_id(role_id=999999)

        assert isinstance(result, RoleNotFoundError)

    async def test_returns_role_with_permissions(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        PermissionSQLFactory(role=role, permission=PermissionType.ADMIN)
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        await db_session.flush()

        # Act
        result = await repository.get_role_by_id(role_id=role.id)

        # Assert
        assert set(result.permissions) == {PermissionType.ADMIN, PermissionType.READ_METRIC}

    async def test_returns_role_with_limits(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        router = RouterSQLFactory()
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=500)
        await db_session.flush()

        # Act
        result = await repository.get_role_by_id(role_id=role.id)

        # Assert
        assert len(result.limits) == 1
        assert result.limits[0].router_id == router.id
        assert result.limits[0].type == LimitType.TPM
        assert result.limits[0].value == 500

    async def test_returns_role_without_permissions_and_limits_when_none_set(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_role_by_id(role_id=role.id)

        # Assert
        assert result.permissions == []
        assert result.limits == []

    async def test_returns_role_with_correct_timestamps(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_role_by_id(role_id=role.id)

        # Assert
        assert isinstance(result.created, int)
        assert isinstance(result.updated, int)
        assert result.created == int(role.created.timestamp())
        assert result.updated == int(role.updated.timestamp())
