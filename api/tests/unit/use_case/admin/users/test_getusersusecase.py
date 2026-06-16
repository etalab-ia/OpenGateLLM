from unittest.mock import AsyncMock

import pytest

from api.domain import EntitiesPage, SortOrder
from api.domain.user.entities import UserSortField
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.admin.users import GetUsersCommand, GetUsersUseCase, GetUsersUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository):
    return GetUsersUseCase(user_repository=user_repository)


@pytest.fixture
def default_command():
    return GetUsersCommand(
        role_id=None,
        organization_id=None,
        offset=0,
        limit=10,
        sort_by=UserSortField.ID,
        sort_order=SortOrder.ASC,
    )


class TestGetUsersUseCase:
    @pytest.mark.asyncio
    async def test_should_return_users_page_with_default_filter(self, use_case, user_repository, default_command):
        # Arrange
        users = [UserFactory(id=10), UserFactory(id=11)]

        user_repository.get_users.return_value = EntitiesPage(total=2, data=users)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetUsersUseCaseSuccess)
        assert result.user_page.total == 2
        assert result.user_page.data == users

    @pytest.mark.asyncio
    async def test_should_return_empty_page(self, use_case, user_repository, default_command):
        # Arrange

        user_repository.get_users.return_value = EntitiesPage(total=0, data=[])

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetUsersUseCaseSuccess)
        assert result.user_page.total == 0
        assert result.user_page.data == []

    @pytest.mark.asyncio
    async def test_should_pass_filters_including_email_search_to_repository(self, use_case, user_repository):
        # Arrange

        user_repository.get_users.return_value = EntitiesPage(total=0, data=[])
        command = GetUsersCommand(
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
        user_repository.get_users.assert_called_once_with(
            role_id=5,
            organization_id=3,
            email="target",
            offset=20,
            limit=50,
            sort_by=UserSortField.EMAIL,
            sort_order=SortOrder.DESC,
        )
