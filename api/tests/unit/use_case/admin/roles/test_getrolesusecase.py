import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain import EntitiesPage, SortField, SortOrder
from api.domain.role.entities import LimitType, PermissionType
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
from api.tests.unit.use_case.factories import LimitFactory, RoleFactory, UserWithRoleFactory
from api.use_cases.admin.roles import GetRolesCommand, GetRolesUseCase, GetRolesUseCaseSuccess


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
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def admin_user():
    return UserWithRoleFactory(id=1, admin=True)


@pytest.fixture
def non_admin_user():
    return UserWithRoleFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def expired_user():
    return UserWithRoleFactory(id=1, expires=int((dt.datetime.now() - dt.timedelta(days=1)).timestamp()))


@pytest.fixture
def use_case(role_repository, permission_repository, limit_repository, user_with_role_query):
    return GetRolesUseCase(
        role_repository=role_repository,
        permission_repository=permission_repository,
        limit_repository=limit_repository,
        user_with_role_query=user_with_role_query,
    )


@pytest.fixture
def default_command():
    return GetRolesCommand(
        user_id=1,
        offset=0,
        limit=10,
        sort_by=SortField.ID,
        sort_order=SortOrder.ASC,
    )


class TestGetRolesUseCase:
    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(
        self, use_case, role_repository, limit_repository, permission_repository, user_with_role_query, non_admin_user, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        role_repository.get_roles_page.assert_not_called()
        limit_repository.get_limits_by_role_ids.assert_not_called()
        permission_repository.get_permissions_by_role_ids.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_empty_page_without_querying_limits_and_permissions(
        self, use_case, role_repository, limit_repository, permission_repository, user_with_role_query, admin_user, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        role_repository.get_roles_page.return_value = EntitiesPage(total=0, data=[])

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetRolesUseCaseSuccess)
        assert result.role_page.total == 0
        assert result.role_page.data == []
        limit_repository.get_limits_by_role_ids.assert_not_called()
        permission_repository.get_permissions_by_role_ids.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_pages_with_roles_permissions_and_limits(
        self, use_case, role_repository, limit_repository, permission_repository, user_with_role_query, admin_user, default_command
    ):
        # Arrange
        role_1 = RoleFactory(id=1, limits=[], permissions=[])
        role_2 = RoleFactory(id=2, limits=[], permissions=[])
        limits_role_1 = [LimitFactory(router_id=1, type=LimitType.RPM, value=100)]
        permissions_role_2 = [PermissionType.READ_METRIC]

        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        role_repository.get_roles_page.return_value = EntitiesPage(total=2, data=[role_1, role_2])
        limit_repository.get_limits_by_role_ids.return_value = {1: limits_role_1}
        permission_repository.get_permissions_by_role_ids.return_value = {2: permissions_role_2}

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetRolesUseCaseSuccess)
        assembled_role_1, assembled_role_2 = result.role_page.data
        assert assembled_role_1.limits == limits_role_1
        assert assembled_role_1.permissions == []
        assert assembled_role_2.limits == []
        assert assembled_role_2.permissions == permissions_role_2
        limit_repository.get_limits_by_role_ids.assert_called_once_with(role_ids=[1, 2])
        permission_repository.get_permissions_by_role_ids.assert_called_once_with(role_ids=[1, 2])
        role_repository.get_roles_page.assert_called_once_with(limit=10, offset=0, sort_by=SortField.ID, sort_order=SortOrder.ASC)

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(self, use_case, expired_user, default_command):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserExpiredError)
