import pytest

from api.domain.user.entities import User
from api.domain.user.errors import UserNotFoundError
from api.infrastructure.postgres import PostgresUserRepository
from api.tests.integration.factories.sql import RoleSQLFactory, UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresUserRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetUserByIssAndSub:
    async def test_returns_user_when_iss_and_sub_match(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()
        UserSQLFactory(email="sso@test.com", role=role, sub="sub-abc", iss="https://issuer.example.com")
        await db_session.flush()

        # Act
        result = await repository.get_user_by_iss_and_sub(iss="https://issuer.example.com", sub="sub-abc")

        # Assert
        assert isinstance(result, User)
        assert result.email == "sso@test.com"
        assert result.sub == "sub-abc"
        assert result.iss == "https://issuer.example.com"

    async def test_returns_not_found_when_iss_and_sub_do_not_match(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()
        UserSQLFactory(email="sso@test.com", role=role, sub="sub-abc", iss="https://issuer.example.com")
        await db_session.flush()

        # Act
        result = await repository.get_user_by_iss_and_sub(iss="https://issuer.example.com", sub="other-sub")

        # Assert
        assert isinstance(result, UserNotFoundError)
