from unittest.mock import MagicMock

import pytest

from api.domain.user.entities import User
from api.domain.user.errors import InvalidUserPasswordError, UserNotFoundError
from api.infrastructure.postgres import PostgresUserRepository
from api.tests.integration.factories.sql import RoleSQLFactory


@pytest.fixture
def user_password_encoder():
    encoder = MagicMock()
    encoder.encode_password.return_value = "encoded:s3cr3t"
    encoder.validate_password.return_value = True
    return encoder


@pytest.fixture
def repository(db_session, user_password_encoder):
    return PostgresUserRepository(postgres_session=db_session, user_password_encoder=user_password_encoder)


@pytest.mark.asyncio(loop_scope="session")
class TestGetUserPasswordByEmailAndPassword:
    async def test_returns_user_when_email_and_password_match(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()
        created = await repository.create_user(email="user@test.com", password="s3cr3t", role_id=role.id)

        # Act
        result = await repository.get_user_password_by_email_and_password(email="user@test.com", password="s3cr3t")

        # Assert
        assert isinstance(result, User)
        assert result.id == created.id
        assert result.email == "user@test.com"

    async def test_returns_user_not_found_error_when_email_does_not_exist(self, repository):
        # Act
        result = await repository.get_user_password_by_email_and_password(email="missing@test.com", password="s3cr3t")

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.email == "missing@test.com"

    async def test_returns_invalid_user_password_error_when_password_is_wrong(self, repository, db_session):
        # Arrange
        repository.user_password_encoder.validate_password.return_value = False
        role = RoleSQLFactory()
        await db_session.flush()
        await repository.create_user(email="user@test.com", password="s3cr3t", role_id=role.id)

        # Act
        result = await repository.get_user_password_by_email_and_password(email="user@test.com", password="wrong-password")

        # Assert
        assert isinstance(result, InvalidUserPasswordError)

    async def test_returns_user_when_password_is_not_set(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()
        await repository.create_user(email="nopassword@test.com", role_id=role.id, password=None)

        # Act
        result = await repository.get_user_password_by_email_and_password(email="nopassword@test.com", password="anything")

        # Assert
        assert isinstance(result, User)
        assert result.email == "nopassword@test.com"
