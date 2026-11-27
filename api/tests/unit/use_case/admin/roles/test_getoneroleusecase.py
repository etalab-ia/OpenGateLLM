from unittest.mock import create_autospec

import pytest

from api.domain.role import RoleAuthorization, RoleRepository
from api.domain.role.errors import RoleNotFoundError, UserCannotReadRoleError
from api.tests.unit.use_case.factories import RoleFactory
from api.use_cases.admin.roles import GetOneRoleCommand, GetOneRoleUseCase, GetOneRoleUseCaseSuccess


@pytest.fixture
def mock_role_repository():
    return create_autospec(RoleRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_role_authorization():
    authorization = create_autospec(RoleAuthorization, instance=True, spec_set=True)
    authorization.can_read_role.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_role_repository, mock_role_authorization):
    return GetOneRoleUseCase(role_repository=mock_role_repository, role_authorization=mock_role_authorization)


class TestGetOneRoleUseCase:
    @pytest.mark.asyncio
    async def test_should_return_the_role_when_the_user_is_allowed_and_the_role_exists(self, use_case, mock_role_repository, mock_role_authorization):
        # Arrange
        role = RoleFactory(id=42)
        mock_role_repository.get_role_with_permissions_and_limits_by_id.return_value = role
        command = GetOneRoleCommand(authenticated_user_id=1, role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetOneRoleUseCaseSuccess)
        assert result.role == role
        mock_role_authorization.can_read_role.assert_awaited_once_with(user_id=1, role_id=42)
        mock_role_repository.get_role_with_permissions_and_limits_by_id.assert_awaited_once_with(role_id=42)

    @pytest.mark.asyncio
    async def test_should_return_an_error_without_reading_anything_when_the_user_is_not_allowed(
        self, use_case, mock_role_repository, mock_role_authorization
    ):
        # Arrange
        mock_role_authorization.can_read_role.return_value = False
        command = GetOneRoleCommand(authenticated_user_id=1, role_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == UserCannotReadRoleError(user_id=1)
        mock_role_repository.get_role_with_permissions_and_limits_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_the_role_does_not_exist(self, use_case, mock_role_repository):
        # Arrange
        mock_role_repository.get_role_with_permissions_and_limits_by_id.return_value = RoleNotFoundError(id=99)
        command = GetOneRoleCommand(authenticated_user_id=1, role_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == RoleNotFoundError(id=99)
        mock_role_repository.get_role_with_permissions_and_limits_by_id.assert_awaited_once_with(role_id=99)
