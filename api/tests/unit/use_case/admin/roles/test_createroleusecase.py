from unittest.mock import AsyncMock

import pytest

from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleAlreadyExistsError
from api.tests.unit.use_case.factories import LimitFactory, RoleFactory
from api.use_cases.admin.roles import CreateRoleCommand, CreateRoleUseCase, CreateRoleUseCaseSuccess


@pytest.fixture
def role_repository():
    return AsyncMock()


@pytest.fixture
def permission_repository():
    return AsyncMock()


@pytest.fixture
def limit_repository():
    return AsyncMock()


@pytest.fixture
def use_case(role_repository, permission_repository, limit_repository):
    return CreateRoleUseCase(
        role_repository=role_repository,
        permission_repository=permission_repository,
        limit_repository=limit_repository,
    )


class TestCreateRoleUseCase:
    @pytest.mark.asyncio
    async def test_should_create_role_with_limits_and_permissions_when_user_is_admin_and_role_does_not_exist(
        self,
        use_case,
        role_repository,
        permission_repository,
        limit_repository,
    ):
        # Arrange
        created_role = RoleFactory(name="created_role")
        limit = LimitFactory()

        role_repository.create_role.return_value = created_role
        permission_repository.create_permissions.return_value = [PermissionType.READ_METRIC]
        limit_repository.create_limits.return_value = [limit]
        command = CreateRoleCommand(name="new_role", permissions=[PermissionType.READ_METRIC], limits=[limit])

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, CreateRoleUseCaseSuccess)
        assert result.role.name == created_role.name
        assert PermissionType.READ_METRIC in result.role.permissions
        assert limit in result.role.limits
        role_repository.create_role.assert_called_once_with(name="new_role")
        permission_repository.create_permissions.assert_awaited_once_with(role_id=created_role.id, permissions=[PermissionType.READ_METRIC])
        limit_repository.create_limits.assert_awaited_once_with(role_id=created_role.id, limits=[limit])

    @pytest.mark.asyncio
    async def test_returns_role_already_exists_error_when_name_conflicts(self, use_case, role_repository):
        # Arrange

        role_repository.create_role.return_value = RoleAlreadyExistsError(name="existing_role")
        command = CreateRoleCommand(name="existing_role", permissions=[], limits=[])

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleAlreadyExistsError)
        assert result.name == "existing_role"
