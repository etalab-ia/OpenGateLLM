from unittest.mock import AsyncMock

import pytest

from api.domain.role.entities import LimitType, PermissionType
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import UserNotFoundError
from api.tests.unit.use_case.factories import LimitFactory, RoleFactory, UserFactory
from api.use_cases.me import GetUserInfoCommand, GetUserInfoUseCase, GetUserInfoUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def role_repository():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository, role_repository):
    return GetUserInfoUseCase(user_repository=user_repository, role_repository=role_repository)


@pytest.fixture
def sample_user():
    return UserFactory(id=42, role_id=7)


class TestGetUserInfoUseCase:
    @pytest.mark.asyncio
    async def test_should_return_user_info_with_accessible_limits(self, use_case, user_repository, role_repository, sample_user):
        # Arrange
        accessible_limit = LimitFactory(router_id=1, type=LimitType.TPM, value=100)
        zero_limit = LimitFactory(router_id=1, type=LimitType.RPM, value=0)
        unlimited_limit = LimitFactory(router_id=2, type=LimitType.TPD, value=None)
        role = RoleFactory(
            id=sample_user.role_id,
            permissions=[PermissionType.READ_METRIC],
            limits=[accessible_limit, zero_limit, unlimited_limit],
        )
        user_repository.get_user_by_id.return_value = sample_user
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = role

        # Act
        result = await use_case.execute(command=GetUserInfoCommand(user_id=sample_user.id))

        # Assert
        assert isinstance(result, GetUserInfoUseCaseSuccess)
        assert result.user_info.id == sample_user.id
        assert result.user_info.email == sample_user.email
        assert result.user_info.name == sample_user.name
        assert result.user_info.organization_id == sample_user.organization_id
        assert result.user_info.budget == sample_user.budget
        assert result.user_info.permissions == [PermissionType.READ_METRIC]
        assert result.user_info.limits == [accessible_limit, unlimited_limit]
        assert result.user_info.expires == sample_user.expires
        assert result.user_info.priority == sample_user.priority
        assert result.user_info.created == sample_user.created
        assert result.user_info.updated == sample_user.updated
        user_repository.get_user_by_id.assert_awaited_once_with(user_id=sample_user.id)
        role_repository.get_role_with_permissions_and_limits_by_id.assert_awaited_once_with(role_id=sample_user.role_id)

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(self, use_case, user_repository, role_repository):
        # Arrange
        non_existing_user_id = 99
        user_repository.get_user_by_id.return_value = UserNotFoundError(id=non_existing_user_id)

        # Act
        result = await use_case.execute(command=GetUserInfoCommand(user_id=non_existing_user_id))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == non_existing_user_id
        user_repository.get_user_by_id.assert_awaited_once_with(user_id=non_existing_user_id)
        role_repository.get_role_with_permissions_and_limits_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_role_does_not_exist(self, use_case, user_repository, role_repository, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user
        role_repository.get_role_with_permissions_and_limits_by_id.return_value = RoleNotFoundError(id=sample_user.role_id)

        # Act
        result = await use_case.execute(command=GetUserInfoCommand(user_id=sample_user.id))

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == sample_user.role_id
        user_repository.get_user_by_id.assert_awaited_once_with(user_id=sample_user.id)
        role_repository.get_role_with_permissions_and_limits_by_id.assert_awaited_once_with(role_id=sample_user.role_id)
