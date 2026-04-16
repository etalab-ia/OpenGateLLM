import pytest

from api.domain import EntitiesPage, SortField, SortOrder
from api.domain.role.entities import Role
from api.infrastructure.postgres import PostgresRolesRepository
from api.tests.integration.factories.sql import RoleSQLFactory, UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresRolesRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetRolesPage:
    async def test_returns_correct_page_with_limit_and_offset(self, repository, db_session):
        # Arrange
        RoleSQLFactory(name="role_a")
        RoleSQLFactory(name="role_b")
        RoleSQLFactory(name="role_c")
        await db_session.flush()

        # Act
        result = await repository.get_roles_page(limit=2, offset=0, sort_by=SortField.NAME, sort_order=SortOrder.ASC)

        # Assert
        assert isinstance(result, EntitiesPage)
        assert all(isinstance(r, Role) for r in result.data)
        returned_names = [r.name for r in result.data]
        assert "role_a" in returned_names
        assert "role_b" in returned_names
        assert "role_c" not in returned_names

    async def test_total_is_consistent_across_pages(self, repository, db_session):
        # Arrange
        for i in range(6):
            RoleSQLFactory(name=f"role_{i}")
        await db_session.flush()

        # Act
        first_page = await repository.get_roles_page(limit=4, offset=0, sort_by=SortField.NAME, sort_order=SortOrder.ASC)
        second_page = await repository.get_roles_page(limit=4, offset=4, sort_by=SortField.NAME, sort_order=SortOrder.ASC)

        # Assert
        assert first_page.total == second_page.total
        first_names = [r.name for r in first_page.data]
        second_names = [r.name for r in second_page.data]
        assert not set(first_names) & set(second_names)

    async def test_sort_by_name_asc(self, repository, db_session):
        # Arrange
        RoleSQLFactory(name="role_c")
        RoleSQLFactory(name="role_a")
        RoleSQLFactory(name="role_b")
        await db_session.flush()

        # Act
        result = await repository.get_roles_page(sort_by=SortField.NAME, sort_order=SortOrder.ASC)

        # Assert
        returned_names = [r.name for r in result.data]
        assert returned_names == ["role_a", "role_b", "role_c"]

    async def test_sort_by_name_desc(self, repository, db_session):
        # Arrange
        RoleSQLFactory(name="role_a")
        RoleSQLFactory(name="role_c")
        RoleSQLFactory(name="role_b")
        await db_session.flush()

        # Act
        result = await repository.get_roles_page(sort_by=SortField.NAME, sort_order=SortOrder.DESC)

        # Assert
        returned_names = [r.name for r in result.data]
        assert returned_names == ["role_c", "role_b", "role_a"]

    async def test_includes_user_count(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory(name="role_with_users")
        UserSQLFactory(role=role)
        UserSQLFactory(role=role)
        await db_session.flush()

        # Act
        result = await repository.get_roles_page()

        # Assert
        returned_role = result.data[0]
        assert returned_role.users == 2

    async def test_returns_empty_data_when_offset_exceeds_total(self, repository, db_session):
        # Arrange
        RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_roles_page(limit=10, offset=2)

        # Assert
        assert result.data == []
        assert result.total == 1
