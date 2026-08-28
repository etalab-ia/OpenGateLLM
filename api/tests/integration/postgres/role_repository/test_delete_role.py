import pytest
from sqlalchemy import select

from api.domain.role.entities import LimitType, PermissionType, Role
from api.domain.role.errors import RoleHasUsersError, RoleNotFoundError
from api.infrastructure.postgres import PostgresRolesRepository
from api.sql.models import Limit as LimitTable
from api.sql.models import Permission as PermissionTable
from api.sql.models import Role as RoleTable
from api.tests.integration.factories.sql import LimitSQLFactory, PermissionSQLFactory, RoleSQLFactory, RouterSQLFactory, UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresRolesRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteRole:
    async def test_returns_none_when_role_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.delete_role(role_id=999999)

        # Assert
        assert result == RoleNotFoundError(id=999999)

    async def test_delete_role_should_delete_role_with_permissions_and_limits(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory(name="to-delete")
        router = RouterSQLFactory()
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=100)
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        await db_session.flush()
        role_id = role.id

        # Act
        delete_result = await repository.delete_role(role_id=role_id)

        # Assert
        assert isinstance(delete_result, Role)
        assert delete_result.id == role.id
        assert delete_result.name == "to-delete"
        limits = (await db_session.execute(select(LimitTable).where(LimitTable.role_id == role_id))).all()
        permissions = (await db_session.execute(select(PermissionTable).where(PermissionTable.role_id == role_id))).all()
        assert limits == []
        assert permissions == []

        get_result = (await db_session.execute(select(RoleTable).where(RoleTable.id == role_id))).all()
        assert get_result == []

    async def test_returns_has_users_error_when_role_still_has_users(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory(name="role-with-users")
        UserSQLFactory(role=role)
        await db_session.flush()

        # Act
        result = await repository.delete_role(role_id=role.id)

        # Assert
        assert isinstance(result, RoleHasUsersError)
        assert result.id == role.id
