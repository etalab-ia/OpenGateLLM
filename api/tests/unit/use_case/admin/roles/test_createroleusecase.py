import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleAlreadyExistsError
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
from api.tests.unit.use_case.factories import LimitFactory, RoleFactory, UserWithRoleFactory
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
def use_case(role_repository, user_with_role_query, permission_repository, limit_repository):
    return CreateRoleUseCase(
        role_repository=role_repository,
        permission_repository=permission_repository,
        limit_repository=limit_repository,
        user_with_role_query=user_with_role_query,
    )


class TestCreateRoleUseCase:
    @pytest.mark.asyncio
    async def test_should_create_role_with_limits_and_permissions_when_user_is_admin_and_role_does_not_exist(
        self,
        use_case,
        role_repository,
        permission_repository,
        limit_repository,
        user_with_role_query,
        admin_user,
    ):
        # Arrange
        created_role = RoleFactory(name="created_role")
        limit = LimitFactory()
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        role_repository.create_role.return_value = created_role
        permission_repository.create_permissions.return_value = [PermissionType.READ_METRIC]
        limit_repository.create_limits.return_value = [limit]
        command = CreateRoleCommand(user_id=1, name="new_role", permissions=[PermissionType.READ_METRIC], limits=[limit])

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
    async def test_returns_user_is_not_admin_error_when_user_is_not_admin(self, use_case, user_with_role_query, non_admin_user):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user
        command = CreateRoleCommand(user_id=1, name="new_role", permissions=[], limits=[])

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UserIsNotAdminError)

    @pytest.mark.asyncio
    async def test_returns_role_already_exists_error_when_name_conflicts(self, use_case, role_repository, user_with_role_query, admin_user):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        role_repository.create_role.return_value = RoleAlreadyExistsError(name="existing_role")
        command = CreateRoleCommand(user_id=1, name="existing_role", permissions=[], limits=[])

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleAlreadyExistsError)
        assert result.name == "existing_role"

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(self, use_case, expired_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=CreateRoleCommand(user_id=1, name="new_role", permissions=[], limits=[]))

        # Assert
        assert isinstance(result, UserExpiredError)
