from unittest.mock import AsyncMock

import pytest

from api.domain.role.errors import RoleHasUsersError, RoleNotFoundError
from api.tests.unit.use_case.factories import RoleFactory
from api.use_cases.admin.roles import DeleteRoleCommand, DeleteRoleUseCase, DeleteRoleUseCaseSuccess


@pytest.fixture
def role_repository():
    return AsyncMock()


@pytest.fixture
def use_case(role_repository):
    return DeleteRoleUseCase(
        role_repository=role_repository,
    )


class TestDeleteRoleUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_role_when_user_is_admin_and_role_exists(self, use_case, role_repository):
        # Arrange
        role = RoleFactory(id=42, users=0)

        role_repository.delete_role.return_value = role
        command = DeleteRoleCommand(role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, DeleteRoleUseCaseSuccess)
        assert result.role == role
        role_repository.delete_role.assert_awaited_once_with(role_id=42)

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_role_does_not_exist(self, use_case, role_repository):
        # Arrange
        role_repository.delete_role.return_value = RoleNotFoundError(id=99)
        command = DeleteRoleCommand(role_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 99
        role_repository.delete_role.assert_awaited_once_with(role_id=99)

    @pytest.mark.asyncio
    async def test_should_return_role_has_users_error_when_role_has_users(self, use_case, role_repository):
        # Arrange
        role_repository.delete_role.return_value = RoleHasUsersError(id=42)
        command = DeleteRoleCommand(role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleHasUsersError)
        assert result.id == 42
        role_repository.delete_role.assert_awaited_once_with(role_id=42)

    @pytest.mark.asyncio
    async def test_should_return_role_has_users_error_when_user_is_added_during_delete_race(self, use_case, role_repository):
        # Arrange
        role_repository.delete_role.return_value = RoleHasUsersError(id=42)
        command = DeleteRoleCommand(role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleHasUsersError)
        assert result.id == 42
        role_repository.delete_role.assert_awaited_once_with(role_id=42)
