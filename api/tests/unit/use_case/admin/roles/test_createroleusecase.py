from unittest.mock import create_autospec

import pytest

from api.domain.role import LimitRepository, PermissionRepository, RoleAuthorization, RoleRepository
from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleAlreadyExistsError, UserCannotCreateRoleError
from api.tests.unit.use_case.factories import LimitFactory, RoleFactory
from api.use_cases.admin.roles import CreateRoleCommand, CreateRoleUseCase, CreateRoleUseCaseSuccess


@pytest.fixture
def mock_role_repository():
    return create_autospec(RoleRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_permission_repository():
    return create_autospec(PermissionRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_limit_repository():
    return create_autospec(LimitRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_role_authorization():
    authorization = create_autospec(RoleAuthorization, instance=True, spec_set=True)
    authorization.can_create_role.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_role_repository, mock_permission_repository, mock_limit_repository, mock_role_authorization):
    return CreateRoleUseCase(
        role_repository=mock_role_repository,
        permission_repository=mock_permission_repository,
        limit_repository=mock_limit_repository,
        role_authorization=mock_role_authorization,
    )


class TestCreateRoleUseCase:
    @pytest.mark.asyncio
    async def test_should_create_role_with_limits_and_permissions_when_the_user_is_allowed_and_the_role_does_not_exist(
        self,
        use_case,
        mock_role_repository,
        mock_permission_repository,
        mock_limit_repository,
        mock_role_authorization,
    ):
        # Arrange
        created_role = RoleFactory(name="created_role")
        limit = LimitFactory()

        mock_role_repository.create_role.return_value = created_role
        mock_permission_repository.create_permissions.return_value = [PermissionType.READ_METRIC]
        mock_limit_repository.create_limits.return_value = [limit]
        command = CreateRoleCommand(authenticated_user_id=1, name="new_role", permissions=[PermissionType.READ_METRIC], limits=[limit])

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, CreateRoleUseCaseSuccess)
        assert result.role.name == created_role.name
        assert PermissionType.READ_METRIC in result.role.permissions
        assert limit in result.role.limits
        mock_role_authorization.can_create_role.assert_awaited_once_with(user_id=1)
        mock_role_repository.create_role.assert_awaited_once_with(name="new_role")
        mock_permission_repository.create_permissions.assert_awaited_once_with(role_id=created_role.id, permissions=[PermissionType.READ_METRIC])
        mock_limit_repository.create_limits.assert_awaited_once_with(role_id=created_role.id, limits=[limit])

    @pytest.mark.asyncio
    async def test_should_return_an_error_without_creating_anything_when_the_user_is_not_allowed(
        self,
        use_case,
        mock_role_repository,
        mock_permission_repository,
        mock_limit_repository,
        mock_role_authorization,
    ):
        # Arrange
        mock_role_authorization.can_create_role.return_value = False
        command = CreateRoleCommand(authenticated_user_id=1, name="new_role", permissions=[], limits=[])

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == UserCannotCreateRoleError(user_id=1)
        mock_role_repository.create_role.assert_not_awaited()
        mock_permission_repository.create_permissions.assert_not_awaited()
        mock_limit_repository.create_limits.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_role_already_exists_error_when_the_name_conflicts(self, use_case, mock_role_repository):
        # Arrange
        mock_role_repository.create_role.return_value = RoleAlreadyExistsError(name="existing_role")
        command = CreateRoleCommand(authenticated_user_id=1, name="existing_role", permissions=[], limits=[])

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == RoleAlreadyExistsError(name="existing_role")
