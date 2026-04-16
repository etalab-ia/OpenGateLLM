import pytest

from api.domain.role.entities import LimitType, PermissionType, Role
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.infrastructure.postgres import PostgresRolesRepository
from api.tests.integration.factories.sql import RoleSQLFactory, RouterSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresRolesRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateRole:
    async def test_updates_role_name_and_returns_updated_role(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory()
        sql_role = RoleSQLFactory(
            name="original-name",
            permissions=[PermissionType.READ_METRIC],
            limits=[{"router": router, "type": LimitType.TPM, "value": 1000}],
        )
        await db_session.flush()
        role = await repository.get_role_with_permissions_and_limits_by_id(role_id=sql_role.id)
        updated_role = role.model_copy(update={"name": "updated-name", "limits": [], "permissions": []})

        # Act
        result = await repository.update_role(updated_role)

        # Assert
        assert isinstance(result, Role)
        assert result.id == sql_role.id
        assert result.name == "updated-name"
        assert result.permissions == []
        assert result.limits == []

    async def test_returns_role_already_exists_error_when_name_conflicts(self, repository, db_session):
        # Arrange
        RoleSQLFactory(name="taken-name")
        sql_role = RoleSQLFactory(name="other-name")
        await db_session.flush()
        role = await repository.get_role_with_permissions_and_limits_by_id(role_id=sql_role.id)
        conflicting_role = role.model_copy(update={"name": "taken-name"})

        # Act
        result = await repository.update_role(conflicting_role)

        # Assert
        assert isinstance(result, RoleAlreadyExistsError)
        assert result.name == "taken-name"

    async def test_returns_role_not_found_error_when_role_does_not_exist(self, repository, db_session):
        # Arrange
        sql_role = RoleSQLFactory()
        await db_session.flush()
        domain_role = await repository.get_role_with_permissions_and_limits_by_id(role_id=sql_role.id)
        non_existent_role = domain_role.model_copy(update={"id": 999999})

        # Act
        result = await repository.update_role(non_existent_role)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.role_id == 999999
