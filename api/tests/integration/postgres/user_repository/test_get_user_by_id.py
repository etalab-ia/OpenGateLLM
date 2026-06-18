from unittest.mock import MagicMock

import pytest

from api.domain.user.entities import User
from api.domain.user.errors import UserNotFoundError
from api.infrastructure.postgres import PostgresUserRepository
from api.tests.integration.factories.sql import OrganizationSQLFactory, RoleSQLFactory, UserSQLFactory


@pytest.fixture
def user_password_encoder():
    return MagicMock()


@pytest.fixture
def repository(db_session, user_password_encoder):
    return PostgresUserRepository(postgres_session=db_session, user_password_encoder=user_password_encoder)


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
        assert result.role == role.id
        assert result.organization_id == organization.id

    async def test_returns_user_not_found_error_when_user_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.get_user_by_id(user_id=999999)

        # Assert
        assert result == UserNotFoundError(id=999999)
