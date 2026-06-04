import pytest

from api.domain.user.entities import User
from api.domain.user.errors import UserNotFoundError
from api.infrastructure.postgres import PostgresUserRepository
from api.tests.integration.factories.sql import UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresUserRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetFirstAdminUser:
    async def test_returns_none_when_no_users_exist(self, repository, db_session):
        # Act
        result = await repository.get_first_admin_user()

        # Assert
        assert result == UserNotFoundError()

    async def test_returns_admin_user_when_admin_user_exists(self, repository, db_session):
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        await db_session.flush()

        # Act
        result = await repository.get_first_admin_user()

        # Assert
        assert isinstance(result, User)
        assert result.id == admin_user.id
        assert result.email == admin_user.email
        assert result.role == admin_user.role_id

    async def test_returns_none_when_user_exists_without_admin_permission(self, repository, db_session):
        # Arrange
        UserSQLFactory(regular_user=True)
        await db_session.flush()

        # Act
        result = await repository.get_first_admin_user()

        # Assert
        assert result == UserNotFoundError()

    async def test_returns_first_admin_user_ordered_by_id(self, repository, db_session):
        # Arrange
        first_admin = UserSQLFactory(admin_user=True)
        UserSQLFactory(regular_user=True)
        second_admin = UserSQLFactory(role=first_admin.role)
        await db_session.flush()

        # Act
        result = await repository.get_first_admin_user()

        # Assert
        assert isinstance(result, User)
        assert result.id == min(first_admin.id, second_admin.id)
