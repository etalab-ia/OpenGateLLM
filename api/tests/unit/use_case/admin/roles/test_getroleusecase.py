from unittest.mock import AsyncMock

import pytest

from api.domain.role.errors import RoleNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.unit.use_case.factories import RoleFactory, UserInfoFactory
from api.use_cases.admin.roles import GetRoleCommand, GetRoleUseCase, GetRoleUseCaseSuccess


@pytest.fixture
def role_repository():
    return AsyncMock()


@pytest.fixture
def user_info_repository():
    return AsyncMock()


@pytest.fixture
def use_case(role_repository, user_info_repository):
    return GetRoleUseCase(
        role_repository=role_repository,
        user_info_repository=user_info_repository,
    )


class TestGetRoleUseCase:
    @pytest.mark.asyncio
    async def test_should_return_role_when_user_is_admin_and_role_exists(self, use_case, role_repository, user_info_repository):
        # Arrange
        role = RoleFactory(id=42)
        user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = role
        command = GetRoleCommand(user_id=1, role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetRoleUseCaseSuccess)
        assert result.role == role
        role_repository.get_role_with_permissions_and_limits_by_id.assert_awaited_once_with(role_id=42)

    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(self, use_case, role_repository, user_info_repository):
        # Arrange
        user_info_repository.get_user_info.return_value = UserInfoFactory(without_permission=True, limits=[])
        command = GetRoleCommand(user_id=1, role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        role_repository.get_role_with_permissions_and_limits_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_role_does_not_exist(self, use_case, role_repository, user_info_repository):
        # Arrange
        user_info_repository.get_user_info.return_value = UserInfoFactory(admin=True)
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = RoleNotFoundError(id=99)
        command = GetRoleCommand(user_id=1, role_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 99
        role_repository.get_role_with_permissions_and_limits_by_id.assert_awaited_once_with(role_id=99)
