from unittest.mock import AsyncMock

import pytest

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import UserAlreadyExistsError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.unit.use_case.factories import UserFactory, UserInfoFactory
from api.use_cases.admin.users import CreateUserCommand, CreateUserUseCase, CreateUserUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def user_info_repository():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository, user_info_repository):
    return CreateUserUseCase(user_repository=user_repository, user_info_repository=user_info_repository)


@pytest.fixture
def command():
    return CreateUserCommand(
        user_id=1,
        email="newuser@test.com",
        password="s3cr3t",
        role_id=10,
    )


class TestCreateUserUseCase:
    @pytest.mark.asyncio
    async def test_should_create_user_when_user_is_admin(self, use_case, user_repository, user_info_repository):
        # Arrange
        user_id = 1
        user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
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
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(self, use_case, user_repository, user_info_repository, command):
        # Arrange
        user_info_repository.get_user_info.return_value = UserInfoFactory(without_permission=True, limits=[])

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        user_repository.create_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_user_already_exists_error_when_a_user_has_the_same_email(
        self, use_case, user_repository, user_info_repository, command
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
        user_repository.create_user.return_value = UserAlreadyExistsError(email="newuser@test.com")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "newuser@test.com"

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_the_role_id_does_not_exist(self, use_case, user_repository, user_info_repository, command):
        # Arrange
        user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
        user_repository.create_user.return_value = RoleNotFoundError(id=10)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 10

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_when_the_organisation_does_not_exist(
        self, use_case, user_repository, user_info_repository, command
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
        user_repository.create_user.return_value = OrganizationNotFoundError(id=5)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 5
