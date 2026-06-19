import pytest

from api.domain import EntitiesPage, SortOrder
from api.domain.user.entities import User, UserSortField
from api.infrastructure.postgres import PostgresUserRepository
from api.tests.integration.factories.sql import OrganizationSQLFactory, RoleSQLFactory, UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresUserRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetUsers:
    async def test_returns_user_page(self, repository, db_session):
        # Arrange
        UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users()

        # Assert
        assert isinstance(result, EntitiesPage)
        assert isinstance(result.total, int)
        assert isinstance(result.data, list)
        assert all(isinstance(u, User) for u in result.data)

    async def test_returns_users_when_no_filter_given(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        user_1 = UserSQLFactory(role=role)
        user_2 = UserSQLFactory(role=role)
        await db_session.flush()

        # Act
        result = await repository.get_users()

        # Assert
        result_ids = {u.id for u in result.data}
        assert {user_1.id, user_2.id}.issubset(result_ids)

    async def test_filters_by_role_id(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        user_1 = UserSQLFactory(role=role)
        user_2 = UserSQLFactory(role=role)
        UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(role_id=role.id)

        # Assert
        result_ids = {u.id for u in result.data}
        assert result_ids == {user_1.id, user_2.id}

    async def test_filters_by_organization_id(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory()
        user_1 = UserSQLFactory(organization=organization)
        user_2 = UserSQLFactory(organization=organization)
        UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(organization_id=organization.id)

        # Assert
        result_ids = {u.id for u in result.data}
        assert result_ids == {user_1.id, user_2.id}

    async def test_filters_by_email_partial_match(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        user = UserSQLFactory(role=role, email="target@test.com")
        UserSQLFactory(role=role, email="other@test.com")
        await db_session.flush()

        # Act
        result = await repository.get_users(email="target")

        # Assert
        assert result.total == 1
        assert [u.id for u in result.data] == [user.id]

    async def test_filters_by_email_matches_shared_substring(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        user_1 = UserSQLFactory(role=role, email="alice@company.com")
        user_2 = UserSQLFactory(role=role, email="bob@company.com")
        UserSQLFactory(role=role, email="other@test.com")
        await db_session.flush()

        # Act
        result = await repository.get_users(email="company")

        # Assert
        assert result.total == 2
        result_ids = {u.id for u in result.data}
        assert result_ids == {user_1.id, user_2.id}

    async def test_total_reflects_role_filter(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        UserSQLFactory(role=role)
        UserSQLFactory(role=role)
        UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(role_id=role.id)

        # Assert
        assert result.total == 2
        assert len(result.data) == 2

    async def test_total_reflects_organization_filter(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory()
        UserSQLFactory(organization=organization)
        UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(organization_id=organization.id)

        # Assert
        assert result.total == 1

    async def test_returns_empty_page_when_no_users_match(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(role_id=role.id)

        # Assert
        assert result.total == 0
        assert result.data == []

    async def test_limit_restricts_number_of_results(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        UserSQLFactory(role=role)
        UserSQLFactory(role=role)
        UserSQLFactory(role=role)
        await db_session.flush()

        # Act
        result = await repository.get_users(role_id=role.id, limit=2)

        # Assert
        assert len(result.data) == 2
        assert result.total == 3

    async def test_offset_skips_results(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        user_1 = UserSQLFactory(role=role)
        user_2 = UserSQLFactory(role=role)
        user_3 = UserSQLFactory(role=role)
        await db_session.flush()

        # Act
        first_page = await repository.get_users(role_id=role.id, limit=10, offset=0, sort_by=UserSortField.ID, sort_order=SortOrder.ASC)
        second_page = await repository.get_users(role_id=role.id, limit=10, offset=1, sort_by=UserSortField.ID, sort_order=SortOrder.ASC)

        # Assert
        assert first_page.data[0].id == user_1.id
        assert [u.id for u in second_page.data] == [user_2.id, user_3.id]

    async def test_sorts_by_email_asc(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        UserSQLFactory(role=role, email="c@test.com")
        UserSQLFactory(role=role, email="a@test.com")
        UserSQLFactory(role=role, email="b@test.com")
        await db_session.flush()

        # Act
        result = await repository.get_users(role_id=role.id, sort_by=UserSortField.EMAIL, sort_order=SortOrder.ASC)

        # Assert
        assert [u.email for u in result.data] == ["a@test.com", "b@test.com", "c@test.com"]

    async def test_sorts_by_email_desc(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        UserSQLFactory(role=role, email="c@test.com")
        UserSQLFactory(role=role, email="a@test.com")
        UserSQLFactory(role=role, email="b@test.com")
        await db_session.flush()

        # Act
        result = await repository.get_users(role_id=role.id, sort_by=UserSortField.EMAIL, sort_order=SortOrder.DESC)

        # Assert
        assert [u.email for u in result.data] == ["c@test.com", "b@test.com", "a@test.com"]
