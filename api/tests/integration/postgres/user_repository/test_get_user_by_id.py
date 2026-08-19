import pytest

from api.domain.user.entities import User
from api.domain.user.errors import UserNotFoundError
from api.infrastructure.postgres import PostgresUserRepository
from api.tests.integration.factories.sql import OrganizationSQLFactory, RoleSQLFactory, UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresUserRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetUserById:
    async def test_returns_user_when_it_exists(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        organization = OrganizationSQLFactory()
        user = UserSQLFactory(role=role, organization=organization)
        await db_session.flush()

        # Act
        result = await repository.get_user_by_id(user_id=user.id)

        # Assert
        assert isinstance(result, User)
        assert result.id == user.id
        assert result.email == user.email
        assert result.role_id == role.id
        assert result.organization_id == organization.id

    async def test_returns_user_not_found_error_when_user_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.get_user_by_id(user_id=999999)

        # Assert
        assert result == UserNotFoundError(id=999999)
