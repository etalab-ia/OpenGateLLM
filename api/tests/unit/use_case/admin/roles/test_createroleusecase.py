from unittest.mock import AsyncMock

import pytest

from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleAlreadyExistsError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.unit.use_case.factories import RoleFactory, UserInfoFactory
from api.use_cases.admin.roles import CreateRoleCommand, CreateRoleUseCase, CreateRoleUseCaseSuccess


@pytest.fixture
def role_repository():
    return AsyncMock()


@pytest.fixture
def user_info_repository():
    return AsyncMock()


@pytest.fixture
def use_case(role_repository, user_info_repository):
    return CreateRoleUseCase(role_repository=role_repository, user_info_repository=user_info_repository)


@pytest.mark.asyncio
async def test_happy_path_returns_success_instance(use_case, role_repository, user_info_repository):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
    role_repository.create_role.return_value = RoleFactory()
    command = CreateRoleCommand(user_id=1, name="new_role", permissions=[], limits=[])

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, CreateRoleUseCaseSuccess)


@pytest.mark.asyncio
async def test_happy_path_result_contains_role_with_correct_name_and_permissions(use_case, role_repository, user_info_repository):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
    role_repository.create_role.return_value = RoleFactory(name="created_role", permissions=[PermissionType.READ_METRIC])
    command = CreateRoleCommand(user_id=1, name="created_role", permissions=[PermissionType.READ_METRIC], limits=[])

    # Act
    result = await use_case.execute(command)

    # Assert
    assert result.role.name == "created_role"
    assert PermissionType.READ_METRIC in result.role.permissions


@pytest.mark.asyncio
async def test_returns_user_is_not_admin_error_when_user_is_not_admin(use_case, user_info_repository):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(without_permission=True, limits=[])
    command = CreateRoleCommand(user_id=1, name="new_role", permissions=[], limits=[])

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, UserIsNotAdminError)


@pytest.mark.asyncio
async def test_returns_role_already_exists_error_when_name_conflicts(use_case, role_repository, user_info_repository):
    # Arrange
    user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
    role_repository.create_role.return_value = RoleAlreadyExistsError(name="existing_role")
    command = CreateRoleCommand(user_id=1, name="existing_role", permissions=[], limits=[])

    # Act
    result = await use_case.execute(command)

    # Assert
    assert isinstance(result, RoleAlreadyExistsError)
    assert result.name == "existing_role"
