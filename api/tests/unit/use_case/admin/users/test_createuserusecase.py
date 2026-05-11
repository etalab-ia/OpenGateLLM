import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import UserAlreadyExistsError, UserExpiredError, UserIsNotAdminError
from api.tests.unit.use_case.factories import UserFactory, UserWithRoleFactory
from api.use_cases.admin.users import CreateUserCommand, CreateUserUseCase, CreateUserUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def admin_user():
    return UserWithRoleFactory(id=1, admin=True)


@pytest.fixture
def non_admin_user():
    return UserWithRoleFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def expired_user():
    return UserWithRoleFactory(id=1, expires=int((dt.datetime.now() - dt.timedelta(days=1)).timestamp()))


@pytest.fixture
def use_case(user_repository, user_with_role_query):
    return CreateUserUseCase(user_repository=user_repository, user_with_role_query=user_with_role_query)


@pytest.fixture
def default_command():
    return CreateUserCommand(
        user_id=1,
        email="newuser@test.com",
        password="s3cr3t",
        role_id=10,
    )


class TestCreateUserUseCase:
    @pytest.mark.asyncio
    async def test_should_create_user_when_user_is_admin(self, use_case, user_repository, user_with_role_query, admin_user):
        # Arrange
        user_id = 1
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        user_repository.create_user.return_value = UserFactory(id=user_id, email="newuser@test.com")
        command = CreateUserCommand(
            user_id=user_id,
            email="newuser@test.com",
            password="s3cr3t",
            role_id=10,
            name="New User",
            organization_id=5,
            budget=100.0,
            priority=2,
        )

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, CreateUserUseCaseSuccess)
        assert result.user.id == user_id
        assert result.user.email == "newuser@test.com"

        user_repository.create_user.assert_awaited_once()
        assert user_repository.create_user.call_args.kwargs == {
            "email": "newuser@test.com",
            "role_id": 10,
            "name": "New User",
            "expires": None,
            "organization_id": 5,
            "password": "s3cr3t",
            "budget": 100.0,
            "priority": 2,
        }

    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(
        self, use_case, user_repository, user_with_role_query, non_admin_user, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        user_repository.create_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_user_already_exists_error_when_a_user_has_the_same_email(
        self, use_case, user_repository, user_with_role_query, admin_user, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        user_repository.create_user.return_value = UserAlreadyExistsError(email="newuser@test.com")

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "newuser@test.com"

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_the_role_id_does_not_exist(
        self, use_case, user_repository, user_with_role_query, admin_user, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        user_repository.create_user.return_value = RoleNotFoundError(id=10)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 10

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_when_the_organisation_does_not_exist(
        self, use_case, user_repository, user_with_role_query, admin_user, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        user_repository.create_user.return_value = OrganizationNotFoundError(id=5)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 5

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(
        self, use_case, user_repository, user_with_role_query, expired_user, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, UserExpiredError)
