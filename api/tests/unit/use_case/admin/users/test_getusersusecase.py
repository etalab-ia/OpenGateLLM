from unittest.mock import create_autospec

import pytest

from api.domain import EntitiesPage, SortOrder
from api.domain.user import UserAuthorization, UserRepository
from api.domain.user.entities import UserSortField
from api.domain.user.errors import UserCannotReadUsersError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.admin.users import GetUsersCommand, GetUsersUseCase, GetUsersUseCaseSuccess


@pytest.fixture
def mock_user_repository():
    return create_autospec(UserRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_user_authorization():
    authorization = create_autospec(UserAuthorization, instance=True, spec_set=True)
    authorization.can_read_users.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_user_repository, mock_user_authorization):
    return GetUsersUseCase(user_repository=mock_user_repository, user_authorization=mock_user_authorization)


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
    async def test_should_return_users_page_with_default_filter(self, use_case, mock_user_repository, default_command):
        # Arrange
        users = [UserFactory(id=10), UserFactory(id=11)]

        mock_user_repository.get_users.return_value = EntitiesPage(total=2, data=users)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetUsersUseCaseSuccess)
        assert result.user_page.total == 2
        assert result.user_page.data == users

    @pytest.mark.asyncio
    async def test_should_return_user_cannot_read_users_error_without_reading_when_the_user_is_not_allowed(
        self, use_case, mock_user_repository, mock_user_authorization, default_command
    ):
        # Arrange
        mock_user_authorization.can_read_users.return_value = False

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserCannotReadUsersError)
        assert result.user_id == 1
        mock_user_authorization.can_read_users.assert_awaited_once_with(user_id=1)
        mock_user_repository.get_users.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_empty_page(self, use_case, mock_user_repository, default_command):
        # Arrange

        mock_user_repository.get_users.return_value = EntitiesPage(total=0, data=[])

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetUsersUseCaseSuccess)
        assert result.user_page.total == 0
        assert result.user_page.data == []

    @pytest.mark.asyncio
    async def test_should_pass_filters_including_email_search_to_repository(self, use_case, mock_user_repository):
        # Arrange

        mock_user_repository.get_users.return_value = EntitiesPage(total=0, data=[])
        command = GetUsersCommand(
            authenticated_user_id=1,
            role_id=5,
            organization_id=3,
            email="target",
            offset=20,
            limit=50,
            sort_by=UserSortField.EMAIL,
            sort_order=SortOrder.DESC,
        )

        # Act
        await use_case.execute(command=command)

        # Assert
        mock_user_repository.get_users.assert_awaited_once_with(
            role_id=5,
            organization_id=3,
            email="target",
            offset=20,
            limit=50,
            sort_by=UserSortField.EMAIL,
            sort_order=SortOrder.DESC,
        )
