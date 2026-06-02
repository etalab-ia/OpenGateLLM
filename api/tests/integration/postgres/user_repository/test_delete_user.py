import pytest
from sqlalchemy import select

from api.domain.user.entities import User
from api.domain.user.errors import DeleteUserWithProvidersError, DeleteUserWithRoutersError, UserNotFoundError
from api.infrastructure.postgres import PostgresUserRepository
from api.sql.models import User as UserTable
from api.tests.integration.factories.sql import ProviderSQLFactory, RouterSQLFactory, UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresUserRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteUser:
    async def test_should_return_deleted_user_when_user_exists(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.delete_user(user_id=user.id)

        # Assert
        assert isinstance(result, User)
        assert result.id == user.id
        assert result.email == user.email
        row = (await db_session.execute(select(UserTable).where(UserTable.id == user.id))).scalar_one_or_none()
        assert row is None

    async def test_should_return_user_not_found_error_when_user_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.delete_user(user_id=999999)

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 999999

    async def test_should_return_delete_user_with_routers_error_when_user_owns_routers(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(user=user, id=1, name="blocking-router")
        await db_session.flush()

        # Act
        result = await repository.delete_user(user_id=user.id)

        # Assert
        assert isinstance(result, DeleteUserWithRoutersError)
        assert result.user_id == user.id
        assert result.router_ids is None
        row = (await db_session.execute(select(UserTable).where(UserTable.id == user.id))).scalar_one_or_none()
        assert row is not None

    async def test_should_return_delete_user_with_providers_error_when_user_owns_providers_on_another_users_router(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        other_router = RouterSQLFactory()
        ProviderSQLFactory(router=other_router, id=1, user=user)
        await db_session.flush()

        # Act
        result = await repository.delete_user(user_id=user.id)

        # Assert
        assert isinstance(result, DeleteUserWithProvidersError)
        assert result.user_id == user.id
        assert result.provider_ids is None
