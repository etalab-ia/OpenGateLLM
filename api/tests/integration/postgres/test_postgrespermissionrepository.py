import pytest
from sqlalchemy import select

from api.domain.role.entities import PermissionType
from api.infrastructure.postgres._postgrespermissionrepository import PostgresPermissionRepository
from api.sql.models import Permission as PermissionTable
from api.tests.integration.factories.sql import PermissionSQLFactory, RoleSQLFactory


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


@pytest.mark.asyncio(loop_scope="session")
class TestDeletePermissionsByRoleId:
    async def test_deletes_all_permissions_for_role_and_returns_them(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory(permissions=[PermissionType.ADMIN, PermissionType.READ_METRIC])
        other_role = RoleSQLFactory(permissions=[PermissionType.CREATE_PUBLIC_COLLECTION])
        await db_session.flush()

        # Act
        result = await repository.delete_permissions_by_role_id(role.id)

        # Assert
        assert set(result) == {PermissionType.ADMIN, PermissionType.READ_METRIC}
        remaining = (await db_session.execute(select(PermissionTable).where(PermissionTable.role_id == other_role.id))).scalars().all()
        assert len(remaining) == 1
        assert remaining[0].permission == PermissionType.CREATE_PUBLIC_COLLECTION
