from unittest.mock import AsyncMock

import pytest

from api.domain.role.errors import RoleHasUsersError, RoleNotFoundError
from api.domain.user.errors import UserIsNotAdminError
from api.tests.unit.use_case.factories import RoleFactory, UserWithRoleFactory
from api.use_cases.admin.roles import DeleteRoleCommand, DeleteRoleUseCase, DeleteRoleUseCaseSuccess


@pytest.fixture
def role_repository():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def use_case(role_repository, user_with_role_query):
    return DeleteRoleUseCase(
        role_repository=role_repository,
        user_with_role_query=user_with_role_query,
    )


class TestDeleteRoleUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_role_when_user_is_admin_and_role_exists(self, use_case, role_repository, user_with_role_query):
        # Arrange
        role = RoleFactory(id=42, users=0)
        user_with_role_query.get_user_with_role_by_id.return_value = UserWithRoleFactory(admin=True)
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = role
        command = DeleteRoleCommand(user_id=1, role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, DeleteRoleUseCaseSuccess)
        assert result.role == role
        role_repository.delete_role.assert_awaited_once_with(role_id=42)

    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(self, use_case, role_repository, user_with_role_query):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = UserWithRoleFactory(without_permission=True, limits=[])
        command = DeleteRoleCommand(user_id=1, role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        role_repository.get_role_with_permissions_and_limits_by_id.assert_not_called()
        role_repository.delete_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_role_does_not_exist(self, use_case, role_repository, user_with_role_query):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = UserWithRoleFactory(admin=True)
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = RoleNotFoundError(id=99)
        command = DeleteRoleCommand(user_id=1, role_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 99
        role_repository.delete_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_role_has_users_error_when_role_has_users(self, use_case, role_repository, user_with_role_query):
        # Arrange
        role = RoleFactory(id=42, users=3)
        user_with_role_query.get_user_with_role_by_id.return_value = UserWithRoleFactory(admin=True)
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = role
        command = DeleteRoleCommand(user_id=1, role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleHasUsersError)
        assert result.id == 42
        role_repository.delete_role.assert_not_called()
