from unittest.mock import AsyncMock

import pytest

from api.domain.user.errors import OrganizationNotFoundError, RoleNotFoundError, UserAlreadyExistsError
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


@pytest.mark.asyncio
async def test_happy_path_returns_success_instance(use_case, user_repository, user_info_repository, command):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
    user_repository.create_user.return_value = UserFactory(email="newuser@test.com")

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, CreateUserUseCaseSuccess)


@pytest.mark.asyncio
async def test_happy_path_result_contains_correct_user(use_case, user_repository, user_info_repository, command):
    # Arrange
    user = UserFactory(id=42, email="newuser@test.com")
    user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
    user_repository.create_user.return_value = user

    # Act
    result = await use_case.execute(command)

    # Assert
    assert result.user.id == 42
    assert result.user.email == "newuser@test.com"


@pytest.mark.asyncio
async def test_happy_path_create_user_is_called_with_correct_args(use_case, user_repository, user_info_repository):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
    user_repository.create_user.return_value = UserFactory()
    command = CreateUserCommand(
        user_id=1,
        email="newuser@test.com",
        password="s3cr3t",
        role_id=10,
        name="New User",
        organization_id=5,
        budget=100.0,
        priority=2,
    )

    # Act
    await use_case.execute(command)

    # Assert
    user_repository.create_user.assert_awaited_once()
    kwargs = user_repository.create_user.call_args.kwargs
    assert kwargs["email"] == "newuser@test.com"
    assert kwargs["role_id"] == 10
    assert kwargs["name"] == "New User"
    assert kwargs["organization_id"] == 5
    assert kwargs["budget"] == 100.0
    assert kwargs["priority"] == 2


@pytest.mark.asyncio
async def test_returns_user_is_not_admin_error_when_user_is_not_admin(use_case, user_info_repository, command):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(without_permission=True, limits=[])

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, UserIsNotAdminError)


@pytest.mark.asyncio
async def test_non_admin_does_not_call_create_user(use_case, user_repository, user_info_repository, command):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(without_permission=True, limits=[])

    # Act
    await use_case.execute(command)

    # Assert
    user_repository.create_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_returns_user_already_exists_error(use_case, user_repository, user_info_repository, command):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
    user_repository.create_user.return_value = UserAlreadyExistsError(email="newuser@test.com")

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, UserAlreadyExistsError)
    assert result.email == "newuser@test.com"


@pytest.mark.asyncio
async def test_returns_role_not_found_error(use_case, user_repository, user_info_repository, command):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
    user_repository.create_user.return_value = RoleNotFoundError(role_id=10)

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, RoleNotFoundError)
    assert result.role_id == 10


@pytest.mark.asyncio
async def test_returns_organization_not_found_error(use_case, user_repository, user_info_repository, command):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
    user_repository.create_user.return_value = OrganizationNotFoundError(organization_id=5)

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, OrganizationNotFoundError)
    assert result.organization_id == 5
