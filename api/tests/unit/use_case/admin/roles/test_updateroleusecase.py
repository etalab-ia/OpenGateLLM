from unittest.mock import AsyncMock

import pytest

from api.domain.role.entities import LimitType, PermissionType
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.tests.unit.use_case.factories import LimitFactory, RoleFactory
from api.use_cases.admin.roles import UpdateRoleCommand, UpdateRoleUseCase, UpdateRoleUseCaseSuccess


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
    return UpdateRoleUseCase(
        role_repository=role_repository,
        permission_repository=permission_repository,
        limit_repository=limit_repository,
    )


@pytest.fixture
def sample_role():
    return RoleFactory(id=1, name="original-role", permissions=[PermissionType.READ_METRIC], limits=[])


@pytest.fixture
def unchanged_command(sample_role):
    """Command replaying the current role state: a full payload that changes nothing."""
    return UpdateRoleCommand(role_id=sample_role.id, name=sample_role.name, permissions=sample_role.permissions, limits=sample_role.limits)


class TestUpdateRoleUseCase:
    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_role_does_not_exist(self, use_case, role_repository, unchanged_command):
        # Arrange
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = RoleNotFoundError(id=1)

        # Act
        result = await use_case.execute(command=unchanged_command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 1
        role_repository.update_role.assert_not_called()
        role_repository.get_role_with_permissions_and_limits_by_id.assert_called_once_with(role_id=1)

    @pytest.mark.asyncio
    async def test_should_not_call_update_role_when_no_fields_are_changed(self, use_case, role_repository, sample_role, unchanged_command):
        # Arrange
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role

        # Act
        result = await use_case.execute(command=unchanged_command)

        # Assert
        assert isinstance(result, UpdateRoleUseCaseSuccess)
        assert result.role == sample_role
        role_repository.update_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_updated_role_when_name_is_changed(self, use_case, role_repository, sample_role):
        # Arrange
        updated_role = sample_role.with_name("new-name")

        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role
        role_repository.update_role.return_value = updated_role

        command = UpdateRoleCommand(role_id=1, name="new-name", permissions=sample_role.permissions, limits=sample_role.limits)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateRoleUseCaseSuccess)
        assert result.role == updated_role
        role_repository.update_role.assert_called_once_with(role=sample_role.with_name("new-name"))

    @pytest.mark.asyncio
    async def test_should_replace_limits_when_limits_are_changed(self, use_case, role_repository, limit_repository, sample_role):
        # Arrange
        new_limits = [LimitFactory(router_id=1, type=LimitType.TPM, value=1000)]
        updated_role = sample_role.with_limits(new_limits)

        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role
        role_repository.update_role.return_value = updated_role

        command = UpdateRoleCommand(role_id=1, name=sample_role.name, permissions=sample_role.permissions, limits=new_limits)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateRoleUseCaseSuccess)
        limit_repository.delete_limits_by_role_id.assert_called_once_with(1)
        limit_repository.create_limits.assert_called_once_with(role_id=sample_role.id, limits=new_limits)

    @pytest.mark.asyncio
    async def test_should_replace_permissions_when_permissions_are_changed(self, use_case, role_repository, permission_repository, sample_role):
        # Arrange
        new_permissions = [PermissionType.ADMIN, PermissionType.READ_METRIC]
        updated_role = sample_role.with_permissions(new_permissions)

        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role
        role_repository.update_role.return_value = updated_role

        command = UpdateRoleCommand(role_id=1, name=sample_role.name, permissions=new_permissions, limits=sample_role.limits)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateRoleUseCaseSuccess)
        permission_repository.delete_permissions_by_role_id.assert_called_once_with(1)
        permission_repository.create_permissions.assert_called_once_with(role_id=sample_role.id, permissions=new_permissions)

    @pytest.mark.asyncio
    async def test_should_update_all_fields_when_all_fields_are_provided(
        self, use_case, role_repository, limit_repository, permission_repository, sample_role
    ):
        # Arrange
        new_limits = [LimitFactory(router_id=2, type=LimitType.RPD, value=500)]
        new_permissions = [PermissionType.ADMIN]
        updated_role = sample_role.with_name("updated").with_limits(new_limits).with_permissions(new_permissions)

        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role
        role_repository.update_role.return_value = updated_role

        command = UpdateRoleCommand(role_id=1, name="updated", permissions=new_permissions, limits=new_limits)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateRoleUseCaseSuccess)
        assert result.role == updated_role
        role_repository.update_role.assert_called_once()
        limit_repository.delete_limits_by_role_id.assert_called_once_with(1)
        limit_repository.create_limits.assert_called_once_with(role_id=sample_role.id, limits=new_limits)
        permission_repository.delete_permissions_by_role_id.assert_called_once_with(1)
        permission_repository.create_permissions.assert_called_once_with(role_id=sample_role.id, permissions=new_permissions)

    @pytest.mark.asyncio
    async def test_should_clear_limits_and_permissions_when_lists_are_empty(self, use_case, role_repository, limit_repository, permission_repository):
        # Arrange
        role = RoleFactory(id=1, name="original-role", permissions=[PermissionType.ADMIN], limits=[LimitFactory(router_id=1, type=LimitType.TPM, value=1000)])  # fmt: off
        cleared_role = role.with_permissions([]).with_limits([])

        role_repository.get_role_with_permissions_and_limits_by_id.return_value = role
        role_repository.update_role.return_value = cleared_role

        command = UpdateRoleCommand(role_id=1, name=role.name, permissions=[], limits=[])

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateRoleUseCaseSuccess)
        assert result.role == cleared_role
        role_repository.update_role.assert_called_once_with(role=cleared_role)
        limit_repository.delete_limits_by_role_id.assert_called_once_with(1)
        limit_repository.create_limits.assert_called_once_with(role_id=role.id, limits=[])
        permission_repository.delete_permissions_by_role_id.assert_called_once_with(1)
        permission_repository.create_permissions.assert_called_once_with(role_id=role.id, permissions=[])

    @pytest.mark.asyncio
    async def test_should_propagate_role_already_exists_error_from_update_role(self, use_case, role_repository, sample_role):
        # Arrange
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role
        role_repository.update_role.return_value = RoleAlreadyExistsError(name="new-name")

        command = UpdateRoleCommand(role_id=1, name="new-name", permissions=sample_role.permissions, limits=sample_role.limits)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, RoleAlreadyExistsError)
        assert result.name == "new-name"
