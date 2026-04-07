import pytest

from api.domain.role.entities import PermissionType
from api.infrastructure.postgres._postgrespermissionrepository import PostgresPermissionRepository
from api.tests.integration.factories import PermissionSQLFactory, RoleSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresPermissionRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestCreatePermissions:
    async def test_returns_empty_list_when_permissions_is_empty(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_permissions(role_id=role.id, permissions=[])

        # Assert
        assert result == []

    async def test_creates_multiple_permissions_and_returns_them(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_permissions(
            role_id=role.id,
            permissions=[PermissionType.ADMIN, PermissionType.READ_METRIC],
        )

        # Assert
        assert set(result) == {PermissionType.ADMIN, PermissionType.READ_METRIC}

    async def test_should_create_only_none_duplicate_limits(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        await db_session.flush()
        # Act
        result = await repository.create_permissions(
            role_id=role.id, permissions=[PermissionType.READ_METRIC, PermissionType.CREATE_PUBLIC_COLLECTION]
        )

        # Assert
        assert result == [PermissionType.CREATE_PUBLIC_COLLECTION]
