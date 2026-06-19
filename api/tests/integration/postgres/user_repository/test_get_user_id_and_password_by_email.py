import pytest

from api.domain.user.errors import UserNotFoundError
from api.infrastructure.postgres import PostgresUserRepository
from api.tests.integration.factories.sql import RoleSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresUserRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetUserIdAndPasswordByEmail:
    async def test_returns_user_id_and_password_when_email_exists(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()
        created = await repository.create_user(email="user@test.com", password="encoded:s3cr3t", role_id=role.id)

        # Act
        result = await repository.get_user_id_and_password_by_email(email="user@test.com")

        # Assert
        assert result == (created.id, "encoded:s3cr3t")

    async def test_returns_user_not_found_error_when_email_does_not_exist(self, repository):
        # Act
        result = await repository.get_user_id_and_password_by_email(email="missing@test.com")

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.email == "missing@test.com"

    async def test_returns_none_password_when_password_is_not_set(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()
        created = await repository.create_user(email="nopassword@test.com", role_id=role.id, password=None)

        # Act
        result = await repository.get_user_id_and_password_by_email(email="nopassword@test.com")

        # Assert
        assert result == (created.id, None)
