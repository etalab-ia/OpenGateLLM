import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain.user.errors import UserExpiredError, UserIsNotAdminError, UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory, UserWithRoleFactory
from api.use_cases.admin.users import GetOneUserCommand, GetOneUserUseCase, GetOneUserUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository, user_with_role_query):
    return GetOneUserUseCase(user_repository=user_repository, user_with_role_query=user_with_role_query)


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
def sample_user():
    return UserFactory(id=42)


class TestGetOneUserUseCase:
    @pytest.mark.asyncio
    async def test_should_return_user_when_user_is_admin(self, use_case, user_repository, user_with_role_query, admin_user, sample_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        use_case.user_repository.get_user_by_id.return_value = sample_user

        # Act
        result = await use_case.execute(command=GetOneUserCommand(authenticated_user_id=admin_user.id, user_id=sample_user.id))

        # Assert
        assert isinstance(result, GetOneUserUseCaseSuccess)
        assert result.user == sample_user
        user_with_role_query.get_user_with_role_by_id.assert_called_once_with(user_id=admin_user.id)
        user_repository.get_user_by_id.assert_called_once_with(user_id=sample_user.id)

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(self, use_case, user_repository, admin_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        non_existing_user_id = 99
        use_case.user_repository.get_user_by_id.return_value = UserNotFoundError(id=non_existing_user_id)

        # Act
        result = await use_case.execute(command=GetOneUserCommand(authenticated_user_id=admin_user.id, user_id=non_existing_user_id))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == non_existing_user_id
        user_repository.get_user_by_id.assert_called_once_with(user_id=non_existing_user_id)

    @pytest.mark.asyncio
    async def test_should_return_insufficient_permission_error_when_user_has_no_permission(self, use_case, user_repository, non_admin_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user

        # Act
        result = await use_case.execute(command=GetOneUserCommand(authenticated_user_id=non_admin_user.id, user_id=42))

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        user_repository.get_user_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(self, use_case, user_repository, expired_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=GetOneUserCommand(authenticated_user_id=expired_user.id, user_id=42))

        # Assert
        assert isinstance(result, UserExpiredError)
        user_repository.get_user_by_id.assert_not_called()
