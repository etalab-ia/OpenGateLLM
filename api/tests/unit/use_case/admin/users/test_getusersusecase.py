import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain import EntitiesPage, SortOrder
from api.domain.user.entities import UserSortField
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
from api.tests.unit.use_case.factories import UserFactory, UserWithRoleFactory
from api.use_cases.admin.users import GetUsersCommand, GetUsersUseCase, GetUsersUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository, user_with_role_query):
    return GetUsersUseCase(user_repository=user_repository, user_with_role_query=user_with_role_query)


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
def default_command():
    return GetUsersCommand(
        authenticated_user_id=1,
        role_id=None,
        organization_id=None,
        offset=0,
        limit=10,
        sort_by=UserSortField.ID,
        sort_order=SortOrder.ASC,
    )


class TestGetUsersUseCase:
    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(
        self, use_case, user_repository, user_with_role_query, non_admin_user, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        user_repository.get_users.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(self, use_case, user_repository, expired_user, default_command):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserExpiredError)
        user_repository.get_users.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_users_page_when_user_is_admin(self, use_case, user_repository, user_with_role_query, admin_user, default_command):
        # Arrange
        users = [UserFactory(id=10), UserFactory(id=11)]
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        user_repository.get_users.return_value = EntitiesPage(total=2, data=users)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetUsersUseCaseSuccess)
        assert result.user_page.total == 2
        assert result.user_page.data == users

    @pytest.mark.asyncio
    async def test_should_return_empty_page(self, use_case, user_repository, user_with_role_query, admin_user, default_command):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        user_repository.get_users.return_value = EntitiesPage(total=0, data=[])

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetUsersUseCaseSuccess)
        assert result.user_page.total == 0
        assert result.user_page.data == []

    @pytest.mark.asyncio
    async def test_should_pass_filters_to_repository(self, use_case, user_repository, user_with_role_query, admin_user):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        user_repository.get_users.return_value = EntitiesPage(total=0, data=[])
        command = GetUsersCommand(
            authenticated_user_id=admin_user.id,
            role_id=5,
            organization_id=3,
            email="target@test.com",
            offset=20,
            limit=50,
            sort_by=UserSortField.EMAIL,
            sort_order=SortOrder.DESC,
        )

        # Act
        await use_case.execute(command=command)

        # Assert
        user_repository.get_users.assert_called_once_with(
            role_id=5,
            organization_id=3,
            email="target@test.com",
            offset=20,
            limit=50,
            sort_by=UserSortField.EMAIL,
            sort_order=SortOrder.DESC,
        )
