import pytest

from api.domain.role.entities import LimitType, PermissionType
from api.infrastructure.postgres import PostgresRolesRepository
from api.tests.integration.factories import LimitSQLFactory, PermissionSQLFactory, RoleSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.exceptions import RoleNotFoundException


@pytest.fixture
def repository(db_session):
    return PostgresRolesRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetRoles:
    async def test_returns_all_roles_when_no_filter_given(self, repository, db_session):
        # Arrange
        role_1 = RoleSQLFactory()
        role_2 = RoleSQLFactory()
        role_3 = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_roles()

        # Assert
        result_ids = {r.id for r in result}
        assert {role_1.id, role_2.id, role_3.id}.issubset(result_ids)

    async def test_filters_by_role_id(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_roles(role_id=role.id)

        # Assert
        assert len(result) == 1
        assert result[0].id == role.id

    async def test_raises_role_not_found_when_filtering_by_unknown_role_id(self, repository, db_session):
        # Act & Assert
        with pytest.raises(RoleNotFoundException):
            await repository.get_roles(role_id=999999)

    async def test_includes_user_count(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        UserSQLFactory(role=role)
        UserSQLFactory(role=role)
        await db_session.flush()

        # Act
        result = await repository.get_roles(role_id=role.id)

        # Assert
        assert result[0].users == 2

    async def test_includes_permissions(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        PermissionSQLFactory(role=role, permission=PermissionType.ADMIN)
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        await db_session.flush()

        # Act
        result = await repository.get_roles(role_id=role.id)

        # Assert
        assert set(result[0].permissions) == {PermissionType.ADMIN, PermissionType.READ_METRIC}

    async def test_includes_limits(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        router = RouterSQLFactory()
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=500)
        await db_session.flush()

        # Act
        result = await repository.get_roles(role_id=role.id)

        # Assert
        assert len(result[0].limits) == 1
        assert result[0].limits[0].router_id == router.id
        assert result[0].limits[0].type == LimitType.TPM
        assert result[0].limits[0].value == 500

    async def test_limit_restricts_number_of_results(self, repository, db_session):
        # Arrange
        RoleSQLFactory()
        RoleSQLFactory()
        RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_roles(limit=2)

        # Assert
        assert len(result) == 2

    async def test_offset_skips_results(self, repository, db_session):
        # Arrange
        RoleSQLFactory(name="role_a")
        RoleSQLFactory(name="role_b")
        RoleSQLFactory(name="role_c")
        await db_session.flush()

        # Act
        first_page = await repository.get_roles(limit=10, offset=0, order_by="name", order_direction="asc")
        second_page = await repository.get_roles(limit=10, offset=1, order_by="name", order_direction="asc")

        # Assert
        assert first_page[0].name == "role_a"
        assert [r.name for r in second_page] == ["role_b", "role_c"]

    async def test_sorts_by_name_asc(self, repository, db_session):
        # Arrange
        RoleSQLFactory(name="role_c")
        RoleSQLFactory(name="role_a")
        RoleSQLFactory(name="role_b")
        await db_session.flush()

        # Act
        result = await repository.get_roles(order_by="name", order_direction="asc")

        # Assert
        names = [r.name for r in result]
        assert names == sorted(names)

    async def test_sorts_by_name_desc(self, repository, db_session):
        # Arrange
        RoleSQLFactory(name="role_c")
        RoleSQLFactory(name="role_a")
        RoleSQLFactory(name="role_b")
        await db_session.flush()

        # Act
        result = await repository.get_roles(order_by="name", order_direction="desc")

        # Assert
        names = [r.name for r in result]
        assert names == sorted(names, reverse=True)
