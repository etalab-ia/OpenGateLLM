import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain import SortField, SortOrder
from api.domain.router.entities import RouterPage
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
from api.tests.unit.use_case.factories import RouterFactory, UserWithRoleFactory
from api.use_cases.admin.routers import GetRoutersCommand, GetRoutersUseCase, GetRoutersUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository, user_with_role_query):
    return GetRoutersUseCase(router_repository=router_repository, user_with_role_query=user_with_role_query)


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
def sample_routers():
    return [RouterFactory(id=1, user_id=1), RouterFactory(id=2, user_id=1)]


@pytest.fixture
def default_command():
    return GetRoutersCommand(user_id=1, offset=0, limit=10, sort_by=SortField.ID, sort_order=SortOrder.ASC)


class TestGetRoutersUseCase:
    @pytest.mark.asyncio
    async def test_should_return_routers_when_user_is_admin(
        self, use_case, router_repository, user_with_role_query, admin_user, sample_routers, default_command
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        use_case.router_repository.get_routers_page.return_value = RouterPage(total=2, data=sample_routers)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetRoutersUseCaseSuccess)
        assert result.router_page.data == sample_routers
        assert result.router_page.total == 2
        user_with_role_query.get_user_with_role_by_id.assert_called_once_with(user_id=admin_user.id)

    @pytest.mark.asyncio
    async def test_should_return_cannot_read_routers_error_when_user_is_not_an_admin(
        self, use_case, router_repository, non_admin_user, default_command
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user

        # Act
        result = await use_case.execute(
            command=GetRoutersCommand(user_id=non_admin_user.id, offset=0, limit=10, sort_by=SortField.ID, sort_order=SortOrder.ASC)
        )

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        router_repository.get_routers_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_forward_pagination_params_to_repository(self, use_case, router_repository, admin_user, sample_routers):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        use_case.router_repository.get_routers_page.return_value = RouterPage(total=2, data=sample_routers)
        command = GetRoutersCommand(user_id=1, offset=5, limit=20, sort_by=SortField.NAME, sort_order=SortOrder.DESC)

        # Act
        await use_case.execute(command=command)

        # Assert
        router_repository.get_routers_page.assert_called_once_with(
            limit=20,
            offset=5,
            sort_by=SortField.NAME,
            sort_order=SortOrder.DESC,
        )

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(self, use_case, expired_user, default_command):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserExpiredError)
