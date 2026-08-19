from datetime import datetime, timedelta

from pydantic import SecretStr
import pytest
from sqlalchemy import select

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError, UserNotFoundError
from api.infrastructure.postgres import PostgresUserRepository
from api.sql.models import User as UserTable
from api.tests.integration.factories.sql import OrganizationSQLFactory, RoleSQLFactory, UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresUserRepository(postgres_session=db_session)


async def _get_user_entity(repository, user_id: int) -> User:
    user = await repository.get_user_by_id(user_id=user_id)
    assert isinstance(user, User)
    return user


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateUser:
    async def test_updates_fields_and_returns_updated_user_entity(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        new_role = RoleSQLFactory()
        new_organization = OrganizationSQLFactory()
        await db_session.flush()
        existing_user = await _get_user_entity(repository, user.id)

        # Act
        result = await repository.update_user(
            user=existing_user.model_copy(
                update={
                    "email": "updated@test.com",
                    "name": "Updated Name",
                    "budget": 50.5,
                    "priority": 3,
                    "password": SecretStr("encoded:new-secret"),
                    "role_id": new_role.id,
                    "organization_id": new_organization.id,
                    "claims": {"name": "Updated Name"},
                }
            )
        )

        # Assert
        assert isinstance(result, User)
        assert result.id == user.id
        assert result.email == "updated@test.com"
        assert result.name == "Updated Name"
        assert result.budget == 50.5
        assert result.priority == 3
        assert result.role_id == new_role.id
        assert result.organization_id == new_organization.id
        assert result.claims == {"name": "Updated Name"}
        assert result.password == SecretStr("encoded:new-secret")
        assert result.expires is None
        row = (await db_session.execute(select(UserTable.password).where(UserTable.id == user.id))).scalar_one()
        assert row == "encoded:new-secret"

    async def test_persists_expires_when_set(self, repository, db_session):
        # Arrange
        user = UserSQLFactory(expires=None)
        await db_session.flush()
        existing_user = await _get_user_entity(repository, user.id)
        expires = int((datetime.now() + timedelta(days=30)).timestamp())

        # Act
        result = await repository.update_user(user=existing_user.model_copy(update={"expires": expires}))

        # Assert
        assert isinstance(result, User)
        assert result.expires == expires

    async def test_returns_user_not_found_error_when_user_does_not_exist(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()
        existing_user = await _get_user_entity(repository, user.id)

        # Act
        result = await repository.update_user(user=existing_user.model_copy(update={"id": 999999}))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 999999

    async def test_returns_user_already_exists_error_when_email_is_duplicate(self, repository, db_session):
        # Arrange
        UserSQLFactory(email="taken@test.com")
        user = UserSQLFactory(email="other@test.com")
        await db_session.flush()
        existing_user = await _get_user_entity(repository, user.id)

        # Act
        result = await repository.update_user(user=existing_user.model_copy(update={"email": "taken@test.com"}))

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "taken@test.com"

    async def test_returns_user_already_exists_error_when_sub_and_iss_are_duplicate(self, repository, db_session):
        # Arrange
        UserSQLFactory(email="taken@test.com", sub="sub-123", iss="https://issuer.example.com")
        user = UserSQLFactory(email="other@test.com", sub="sub-456", iss="https://other-issuer.example.com")
        await db_session.flush()
        existing_user = await _get_user_entity(repository, user.id)

        # Act
        result = await repository.update_user(user=existing_user.model_copy(update={"sub": "sub-123", "iss": "https://issuer.example.com"}))

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "other@test.com"

    async def test_returns_role_not_found_error_when_role_does_not_exist(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()
        existing_user = await _get_user_entity(repository, user.id)

        # Act
        result = await repository.update_user(user=existing_user.model_copy(update={"role_id": 999999}))

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 999999

    async def test_returns_organization_not_found_error_when_organization_does_not_exist(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()
        existing_user = await _get_user_entity(repository, user.id)

        # Act
        result = await repository.update_user(user=existing_user.model_copy(update={"organization_id": 999999}))

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 999999
