import pytest

from api.infrastructure.postgres import PostgresUserRepository
from api.tests.integration.factories import UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresUserRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestHasAdminUser:
    async def test_returns_false_when_no_users_exist(self, repository, db_session):
        result = await repository.has_admin_user()

        assert result is False

    async def test_returns_true_when_admin_user_exists(self, repository, db_session):
        UserSQLFactory(admin_user=True)
        await db_session.flush()

        result = await repository.has_admin_user()

        assert result is True

    async def test_returns_false_when_user_exists_without_admin_permission(self, repository, db_session):
        UserSQLFactory(regular_user=True)
        await db_session.flush()

        result = await repository.has_admin_user()

        assert result is False
