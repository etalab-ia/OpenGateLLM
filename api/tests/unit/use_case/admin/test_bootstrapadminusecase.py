from unittest.mock import AsyncMock

import pytest

from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleAlreadyExistsError
from api.domain.user.errors import UserAlreadyExistsError
from api.tests.unit.use_case.factories import RoleFactory, UserFactory
from api.use_cases.admin.bootstrapadminusecase import (
    BootstrapAdminCommand,
    BootstrapAdminUseCase,
    BootstrapAdminUseCaseSkipped,
    BootstrapAdminUseCaseSuccess,
)


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def role_repository():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository, role_repository):
    return BootstrapAdminUseCase(user_repository=user_repository, role_repository=role_repository)


@pytest.fixture
def command():
    return BootstrapAdminCommand(
        name="admin",
        email="admin@opengatellm.org",
        password="s3cr3t",
        permissions=[PermissionType.ADMIN],
        limits=[],
    )


@pytest.mark.asyncio
async def test_happy_path_returns_success_instance(use_case, user_repository, role_repository, command):
    # Arrange
    user_repository.has_admin_user.return_value = False
    role_repository.create_role.return_value = RoleFactory()
    user_repository.create_user.return_value = UserFactory(email="admin@opengatellm.org")

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, BootstrapAdminUseCaseSuccess)


@pytest.mark.asyncio
async def test_happy_path_result_contains_correct_email_and_ids(use_case, user_repository, role_repository, command):
    # Arrange
    role = RoleFactory(id=42)
    user = UserFactory(id=10, email="admin@opengatellm.org")
    user_repository.has_admin_user.return_value = False
    role_repository.create_role.return_value = role
    user_repository.create_user.return_value = user

    # Act
    result = await use_case.execute(command)

    # Assert
    assert result.email == "admin@opengatellm.org"
    assert result.user_id == 10
    assert result.role_id == 42


@pytest.mark.asyncio
async def test_happy_path_create_user_is_called_with_correct_role_id(use_case, user_repository, role_repository, command):
    # Arrange
    role = RoleFactory(id=42)
    user_repository.has_admin_user.return_value = False
    role_repository.create_role.return_value = role
    user_repository.create_user.return_value = UserFactory()

    # Act
    await use_case.execute(command)

    # Assert
    user_repository.create_user.assert_awaited_once()
    assert user_repository.create_user.call_args.kwargs["role_id"] == 42


@pytest.mark.asyncio
async def test_skips_when_admin_user_already_exists(use_case, user_repository, command):
    # Arrange
    user_repository.has_admin_user.return_value = True

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, BootstrapAdminUseCaseSkipped)


@pytest.mark.asyncio
async def test_skip_does_not_call_create_role_or_create_user(use_case, user_repository, role_repository, command):
    # Arrange
    user_repository.has_admin_user.return_value = True

    # Act
    await use_case.execute(command)

    # Assert
    role_repository.create_role.assert_not_awaited()
    user_repository.create_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_returns_role_already_exists_error_when_role_name_conflicts(use_case, user_repository, role_repository, command):
    # Arrange
    user_repository.has_admin_user.return_value = False
    role_repository.create_role.return_value = RoleAlreadyExistsError(name="admin")

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, RoleAlreadyExistsError)
    assert result.name == "admin"


@pytest.mark.asyncio
async def test_returns_user_already_exists_error_when_email_conflicts(use_case, user_repository, role_repository, command):
    # Arrange
    user_repository.has_admin_user.return_value = False
    role_repository.create_role.return_value = RoleFactory()
    user_repository.create_user.return_value = UserAlreadyExistsError(email="admin@opengatellm.org")

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, UserAlreadyExistsError)
    assert result.email == "admin@opengatellm.org"


@pytest.mark.asyncio
async def test_custom_username_is_used_as_email(use_case, user_repository, role_repository):
    # Arrange
    user_repository.has_admin_user.return_value = False
    role_repository.create_role.return_value = RoleFactory()
    user_repository.create_user.return_value = UserFactory(email="superadmin")
    command = BootstrapAdminCommand(
        name="superadmin",
        email="superadmin",
        password="s3cr3t",
        permissions=[PermissionType.ADMIN],
        limits=[],
    )

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, BootstrapAdminUseCaseSuccess)
    assert result.email == "superadmin"


@pytest.mark.asyncio
async def test_custom_password_is_accepted(use_case, user_repository, role_repository):
    # Arrange
    user_repository.has_admin_user.return_value = False
    role_repository.create_role.return_value = RoleFactory()
    user_repository.create_user.return_value = UserFactory()
    command = BootstrapAdminCommand(
        name="customadmin",
        email="customadmin",
        password="my-strong-pass",
        permissions=[PermissionType.ADMIN],
        limits=[],
    )

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, BootstrapAdminUseCaseSuccess)
