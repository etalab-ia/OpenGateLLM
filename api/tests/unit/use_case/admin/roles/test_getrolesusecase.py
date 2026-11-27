from unittest.mock import create_autospec

import pytest

from api.domain import EntitiesPage, SortField, SortOrder
from api.domain.role import LimitRepository, PermissionRepository, RoleAuthorization, RoleRepository
from api.domain.role.entities import LimitType, PermissionType
from api.domain.role.errors import UserCannotReadRolesError
from api.tests.unit.use_case.factories import LimitFactory, RoleFactory
from api.use_cases.admin.roles import GetRolesCommand, GetRolesUseCase, GetRolesUseCaseSuccess


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
    authorization.can_read_roles.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_role_repository, mock_permission_repository, mock_limit_repository, mock_role_authorization):
    return GetRolesUseCase(
        role_repository=mock_role_repository,
        permission_repository=mock_permission_repository,
        limit_repository=mock_limit_repository,
        role_authorization=mock_role_authorization,
    )


@pytest.fixture
def default_command():
    return GetRolesCommand(
        authenticated_user_id=1,
        offset=0,
        limit=10,
        sort_by=SortField.ID,
        sort_order=SortOrder.ASC,
    )


class TestGetRolesUseCase:
    @pytest.mark.asyncio
    async def test_should_return_an_error_without_reading_anything_when_the_user_is_not_allowed(
        self, use_case, mock_role_repository, mock_role_authorization, default_command
    ):
        # Arrange
        mock_role_authorization.can_read_roles.return_value = False

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert result == UserCannotReadRolesError(user_id=1)
        mock_role_authorization.can_read_roles.assert_awaited_once_with(user_id=1)
        mock_role_repository.get_roles_page.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_an_empty_page_without_querying_limits_and_permissions_when_there_is_no_role(
        self, use_case, mock_role_repository, mock_limit_repository, mock_permission_repository, default_command
    ):
        # Arrange
        mock_role_repository.get_roles_page.return_value = EntitiesPage(total=0, data=[])

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetRolesUseCaseSuccess)
        assert result.role_page.total == 0
        assert result.role_page.data == []
        mock_limit_repository.get_limits_by_role_ids.assert_not_awaited()
        mock_permission_repository.get_permissions_by_role_ids.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_the_page_with_the_roles_permissions_and_limits_when_the_user_is_allowed(
        self, use_case, mock_role_repository, mock_limit_repository, mock_permission_repository, mock_role_authorization, default_command
    ):
        # Arrange
        role_1 = RoleFactory(id=1, limits=[], permissions=[])
        role_2 = RoleFactory(id=2, limits=[], permissions=[])
        limits_role_1 = [LimitFactory(router_id=1, type=LimitType.RPM, value=100)]
        permissions_role_2 = [PermissionType.READ_METRIC]

        mock_role_repository.get_roles_page.return_value = EntitiesPage(total=2, data=[role_1, role_2])
        mock_limit_repository.get_limits_by_role_ids.return_value = {1: limits_role_1}
        mock_permission_repository.get_permissions_by_role_ids.return_value = {2: permissions_role_2}

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetRolesUseCaseSuccess)
        assembled_role_1, assembled_role_2 = result.role_page.data
        assert assembled_role_1.limits == limits_role_1
        assert assembled_role_1.permissions == []
        assert assembled_role_2.limits == []
        assert assembled_role_2.permissions == permissions_role_2
        mock_role_authorization.can_read_roles.assert_awaited_once_with(user_id=1)
        mock_role_repository.get_roles_page.assert_awaited_once_with(limit=10, offset=0, sort_by=SortField.ID, sort_order=SortOrder.ASC)
        mock_limit_repository.get_limits_by_role_ids.assert_awaited_once_with(role_ids=[1, 2])
        mock_permission_repository.get_permissions_by_role_ids.assert_awaited_once_with(role_ids=[1, 2])
