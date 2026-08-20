from unittest.mock import AsyncMock

import pytest

from api.domain.role.errors import RoleNotFoundError
from api.tests.unit.use_case.factories import RoleFactory
from api.use_cases.admin.roles import GetOneRoleCommand, GetOneRoleUseCase, GetOneRoleUseCaseSuccess


@pytest.fixture
def role_repository():
    return AsyncMock()


@pytest.fixture
def use_case(role_repository):
    return GetOneRoleUseCase(role_repository=role_repository)


class TestGetOneRoleUseCase:
    @pytest.mark.asyncio
    async def test_should_return_role_when_user_is_admin_and_role_exists(self, use_case, role_repository):
        # Arrange
        role = RoleFactory(id=42)
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = role
        command = GetOneRoleCommand(role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetOneRoleUseCaseSuccess)
        assert result.role == role
        role_repository.get_role_with_permissions_and_limits_by_id.assert_awaited_once_with(role_id=42)

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_role_does_not_exist(self, use_case, role_repository):
        # Arrange
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = RoleNotFoundError(id=99)
        command = GetOneRoleCommand(role_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 99
        role_repository.get_role_with_permissions_and_limits_by_id.assert_awaited_once_with(role_id=99)
