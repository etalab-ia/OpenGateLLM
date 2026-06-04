import bcrypt
import pytest
from sqlalchemy import select

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError
from api.infrastructure.postgres import PostgresUserRepository
from api.sql.models import User as UserTable
from api.tests.integration.factories.sql import OrganizationSQLFactory, RoleSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresUserRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestCreateUser:
    async def test_creates_user_and_returns_user_entity(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_user(email="user@test.com", password="s3cr3t", role_id=role.id)

        # Assert
        assert isinstance(result, User)
        assert result.email == "user@test.com"
        assert isinstance(result.id, int)
        assert result.role == role.id

    async def test_password_is_hashed_in_db(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        await repository.create_user(email="hashed@test.com", password="plaintext", role_id=role.id)
        await db_session.flush()

        # Assert
        row = (await db_session.execute(select(UserTable.password).where(UserTable.email == "hashed@test.com"))).scalar_one()
        assert row != "plaintext"
        assert bcrypt.checkpw(b"plaintext", row.encode("utf-8"))

    async def test_returns_user_already_exists_error_when_email_is_duplicate(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()
        await repository.create_user(email="duplicate@test.com", password="s3cr3t", role_id=role.id)

        # Act
        result = await repository.create_user(email="duplicate@test.com", password="other", role_id=role.id)

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "duplicate@test.com"

    async def test_returns_role_not_found_error_when_role_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.create_user(email="user@test.com", password="s3cr3t", role_id=999999)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 999999

    async def test_returns_organization_not_found_error_when_organization_does_not_exist(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_user(email="user@test.com", password="s3cr3t", role_id=role.id, organization_id=999999)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 999999

    async def test_creates_user_with_all_optional_fields(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        organization = OrganizationSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_user(
            email="full@test.com",
            password="s3cr3t",
            role_id=role.id,
            name="Full User",
            sub="sub-123",
            iss="https://issuer.example.com",
            organization_id=organization.id,
            budget=100.0,
            priority=5,
        )

        # Assert
        assert isinstance(result, User)
        assert result.name == "Full User"
        assert result.sub == "sub-123"
        assert result.iss == "https://issuer.example.com"
        assert result.organization == organization.id
        assert result.budget == 100.0
        assert result.priority == 5
