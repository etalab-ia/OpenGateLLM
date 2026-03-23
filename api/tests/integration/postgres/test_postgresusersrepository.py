import bcrypt
import pytest
from sqlalchemy import select

from api.domain.user.entities import User
from api.domain.user.errors import OrganizationNotFoundError, RoleNotFoundError, UserAlreadyExistsError
from api.infrastructure.postgres import PostgresUserRepository
from api.sql.models import User as UserTable
from api.tests.integration.factories import OrganizationSQLFactory, RoleSQLFactory, UserSQLFactory
from api.utils.exceptions import UserNotFoundException


@pytest.fixture
def repository(db_session):
    return PostgresUserRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestHasAdminUser:
    async def test_returns_false_when_no_users_exist(self, repository, db_session):
        # Act
        result = await repository.has_admin_user()

        # Assert
        assert result is False

    async def test_returns_true_when_admin_user_exists(self, repository, db_session):
        # Arrange
        UserSQLFactory(admin_user=True)
        await db_session.flush()

        # Act
        result = await repository.has_admin_user()

        # Assert
        assert result is True

    async def test_returns_false_when_user_exists_without_admin_permission(self, repository, db_session):
        # Arrange
        UserSQLFactory(regular_user=True)
        await db_session.flush()

        # Act
        result = await repository.has_admin_user()

        # Assert
        assert result is False


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
        assert result.role_id == 999999

    async def test_returns_organization_not_found_error_when_organization_does_not_exist(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_user(email="user@test.com", password="s3cr3t", role_id=role.id, organization_id=999999)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.organization_id == 999999

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


@pytest.mark.asyncio(loop_scope="session")
class TestGetUsers:
    async def test_returns_all_users_when_no_filter_given(self, repository, db_session):
        # Arrange
        user_1 = UserSQLFactory()
        user_2 = UserSQLFactory()
        user_3 = UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users()

        # Assert
        result_ids = {u.id for u in result}
        assert {user_1.id, user_2.id, user_3.id}.issubset(result_ids)

    async def test_filters_by_email(self, repository, db_session):
        # Arrange
        user = UserSQLFactory(email="findme@test.com")
        UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(email="findme@test.com")

        # Assert
        assert len(result) == 1
        assert result[0].id == user.id

    async def test_filters_by_user_id(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(user_id=user.id)

        # Assert
        assert len(result) == 1
        assert result[0].id == user.id

    async def test_filters_by_role_id(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        user_1 = UserSQLFactory(role=role)
        user_2 = UserSQLFactory(role=role)
        UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(role_id=role.id)

        # Assert
        result_ids = {u.id for u in result}
        assert result_ids == {user_1.id, user_2.id}

    async def test_filters_by_organization_id(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory()
        user_1 = UserSQLFactory(organization=organization)
        user_2 = UserSQLFactory(organization=organization)
        UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(organization_id=organization.id)

        # Assert
        result_ids = {u.id for u in result}
        assert result_ids == {user_1.id, user_2.id}

    async def test_limit_restricts_number_of_results(self, repository, db_session):
        # Arrange
        UserSQLFactory()
        UserSQLFactory()
        UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(limit=2)

        # Assert
        assert len(result) == 2

    async def test_offset_skips_results(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        user_1 = UserSQLFactory(role=role)
        user_2 = UserSQLFactory(role=role)
        user_3 = UserSQLFactory(role=role)
        await db_session.flush()

        # Act
        first_page = await repository.get_users(role_id=role.id, limit=10, offset=0, order_by="id", order_direction="asc")
        second_page = await repository.get_users(role_id=role.id, limit=10, offset=1, order_by="id", order_direction="asc")

        # Assert
        assert first_page[0].id == user_1.id
        assert [u.id for u in second_page] == [user_2.id, user_3.id]

    async def test_sorts_by_email_asc(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        UserSQLFactory(role=role, email="c@test.com")
        UserSQLFactory(role=role, email="a@test.com")
        UserSQLFactory(role=role, email="b@test.com")
        await db_session.flush()

        # Act
        result = await repository.get_users(role_id=role.id, order_by="email", order_direction="asc")

        # Assert
        assert [u.email for u in result] == ["a@test.com", "b@test.com", "c@test.com"]

    async def test_sorts_by_email_desc(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        UserSQLFactory(role=role, email="c@test.com")
        UserSQLFactory(role=role, email="a@test.com")
        UserSQLFactory(role=role, email="b@test.com")
        await db_session.flush()

        # Act
        result = await repository.get_users(role_id=role.id, order_by="email", order_direction="desc")

        # Assert
        assert [u.email for u in result] == ["c@test.com", "b@test.com", "a@test.com"]

    async def test_raises_user_not_found_when_filtering_by_unknown_user_id(self, repository, db_session):
        # Act & Assert
        with pytest.raises(UserNotFoundException):
            await repository.get_users(user_id=999999)

    async def test_raises_user_not_found_when_filtering_by_unknown_email(self, repository, db_session):
        # Act & Assert
        with pytest.raises(UserNotFoundException):
            await repository.get_users(email="unknown@test.com")

    async def test_returns_empty_list_when_no_users_match_role_id(self, repository, db_session):
        # Arrange
        role = RoleSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(role_id=role.id)

        # Assert
        assert result == []

    async def test_returns_empty_list_when_no_users_match_organization_id(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.get_users(organization_id=organization.id)

        # Assert
        assert result == []


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateUser:
    async def test_raises_not_implemented_error(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()

        # Act & Assert
        with pytest.raises(NotImplementedError):
            await repository.update_user(user)


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteUser:
    async def test_raises_not_implemented_error(self, repository, db_session):
        # Act & Assert
        with pytest.raises(NotImplementedError):
            await repository.delete_user(user_id=1)
