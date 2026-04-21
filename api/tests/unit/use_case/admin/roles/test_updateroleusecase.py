from unittest.mock import AsyncMock

import pytest

from api.domain.role.entities import LimitType, PermissionType
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.unit.use_case.factories import LimitFactory, RoleFactory, UserInfoFactory
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
def user_info_repository():
    return AsyncMock()


@pytest.fixture
def use_case(role_repository, permission_repository, limit_repository, user_info_repository):
    return UpdateRoleUseCase(
        role_repository=role_repository,
        permission_repository=permission_repository,
        limit_repository=limit_repository,
        user_info_repository=user_info_repository,
    )


@pytest.fixture
def admin_user_info():
    return UserInfoFactory(admin=True)


@pytest.fixture
def unauthorized_user_info():
    return UserInfoFactory(without_permission=True, limits=[])


@pytest.fixture
def sample_role():
    return RoleFactory(id=1, name="original-role", permissions=[PermissionType.READ_METRIC], limits=[])


@pytest.fixture
def default_command():
    return UpdateRoleCommand(
        user_id=1,
        role_id=1,
        name=None,
        permissions=None,
        limits=None,
    )


class TestUpdateRoleUseCase:
    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(
        self, use_case, role_repository, user_info_repository, unauthorized_user_info, default_command
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = unauthorized_user_info

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        role_repository.get_role_with_permissions_and_limits_by_id.assert_not_called()
        role_repository.update_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_role_does_not_exist(
        self, use_case, role_repository, user_info_repository, admin_user_info, default_command
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = None

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 1
        role_repository.update_role.assert_not_called()
        role_repository.get_role_with_permissions_and_limits_by_id.assert_called_once_with(role_id=1)

    @pytest.mark.asyncio
    async def test_should_not_call_update_role_when_no_fields_are_changed(
        self, use_case, role_repository, user_info_repository, admin_user_info, sample_role, default_command
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UpdateRoleUseCaseSuccess)
        assert result.role == sample_role
        role_repository.update_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_updated_role_when_name_is_changed(
        self, use_case, role_repository, user_info_repository, admin_user_info, sample_role
    ):
        # Arrange
        updated_role = sample_role.with_name("new-name")
        user_info_repository.get_user_info.return_value = admin_user_info
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role
        role_repository.update_role.return_value = updated_role

        command = UpdateRoleCommand(user_id=1, role_id=1, name="new-name", permissions=None, limits=None)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateRoleUseCaseSuccess)
        assert result.role == updated_role
        role_repository.update_role.assert_called_once_with(sample_role.with_name("new-name"))

    @pytest.mark.asyncio
    async def test_should_replace_limits_when_limits_are_changed(
        self, use_case, role_repository, limit_repository, user_info_repository, admin_user_info, sample_role
    ):
        # Arrange
        new_limits = [LimitFactory(router_id=1, type=LimitType.TPM, value=1000)]
        updated_role = sample_role.with_limits(new_limits)
        user_info_repository.get_user_info.return_value = admin_user_info
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role
        role_repository.update_role.return_value = updated_role

        command = UpdateRoleCommand(user_id=1, role_id=1, name=None, permissions=None, limits=new_limits)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateRoleUseCaseSuccess)
        limit_repository.delete_limits_by_role_id.assert_called_once_with(1)
        limit_repository.create_limits.assert_called_once_with(role_id=sample_role.id, limits=new_limits)

    @pytest.mark.asyncio
    async def test_should_replace_permissions_when_permissions_are_changed(
        self, use_case, role_repository, permission_repository, user_info_repository, admin_user_info, sample_role
    ):
        # Arrange
        new_permissions = [PermissionType.ADMIN, PermissionType.READ_METRIC]
        updated_role = sample_role.with_permissions(new_permissions)
        user_info_repository.get_user_info.return_value = admin_user_info
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role
        role_repository.update_role.return_value = updated_role

        command = UpdateRoleCommand(user_id=1, role_id=1, name=None, permissions=new_permissions, limits=None)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UpdateRoleUseCaseSuccess)
        permission_repository.delete_permissions_by_role_id.assert_called_once_with(1)
        permission_repository.create_permissions.assert_called_once_with(role_id=sample_role.id, permissions=new_permissions)

    @pytest.mark.asyncio
    async def test_should_update_all_fields_when_all_fields_are_provided(
        self, use_case, role_repository, limit_repository, permission_repository, user_info_repository, admin_user_info, sample_role
    ):
        # Arrange
        new_limits = [LimitFactory(router_id=2, type=LimitType.RPD, value=500)]
        new_permissions = [PermissionType.ADMIN]
        updated_role = sample_role.with_name("updated").with_limits(new_limits).with_permissions(new_permissions)
        user_info_repository.get_user_info.return_value = admin_user_info
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role
        role_repository.update_role.return_value = updated_role

        command = UpdateRoleCommand(user_id=1, role_id=1, name="updated", permissions=new_permissions, limits=new_limits)

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
    async def test_should_propagate_role_already_exists_error_from_update_role(
        self, use_case, role_repository, user_info_repository, admin_user_info, sample_role
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = sample_role
        role_repository.update_role.return_value = RoleAlreadyExistsError(name="new-name")

        command = UpdateRoleCommand(user_id=1, role_id=1, name="new-name", permissions=None, limits=None)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, RoleAlreadyExistsError)
        assert result.name == "new-name"
