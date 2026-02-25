from unittest.mock import AsyncMock

import pytest

from api.domain.router.entities import RouterPage, RouterSortField, SortOrder
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.unit.use_case.factories import RouterFactory, UserInfoFactory
from api.use_cases.admin.routers import GetRoutersCommand, GetRoutersUseCase, GetRoutersUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def user_info_repository():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository, user_info_repository):
    return GetRoutersUseCase(router_repository=router_repository, user_info_repository=user_info_repository)


@pytest.fixture
def admin_user_info():
    return UserInfoFactory(id=1, admin=True)


@pytest.fixture
def unauthorized_user_info():
    return UserInfoFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def sample_routers():
    return [RouterFactory(id=1, user_id=1), RouterFactory(id=2, user_id=1)]


@pytest.fixture
def sample_command():
    return GetRoutersCommand(user_id=1, offset=0, limit=10, sort_by=RouterSortField.ID, sort_order=SortOrder.ASC)


class TestGetRoutersUseCase:
    @pytest.mark.asyncio
    async def test_should_return_routers_when_user_is_admin(
        self, use_case, router_repository, user_info_repository, admin_user_info, sample_routers, sample_command
    ):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_routers_page.return_value = RouterPage(total=2, data=sample_routers)

        # Act
        result = await use_case.execute(command=sample_command)

        # Assert
        assert isinstance(result, GetRoutersUseCaseSuccess)
        assert result.routers == sample_routers
        assert result.total == 2
        user_info_repository.get_user_info.assert_called_once_with(user_id=admin_user_info.id)

    @pytest.mark.asyncio
    async def test_should_return_cannot_read_routers_error_when_user_is_not_an_admin(
        self, use_case, router_repository, unauthorized_user_info, sample_command
    ):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = unauthorized_user_info

        # Act
        result = await use_case.execute(
            command=GetRoutersCommand(user_id=unauthorized_user_info.id, offset=0, limit=10, sort_by=RouterSortField.ID, sort_order=SortOrder.ASC)
        )

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        router_repository.get_routers_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_forward_pagination_params_to_repository(self, use_case, router_repository, admin_user_info, sample_routers):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_routers_page.return_value = RouterPage(total=2, data=sample_routers)
        command = GetRoutersCommand(user_id=1, offset=5, limit=20, sort_by=RouterSortField.NAME, sort_order=SortOrder.DESC)

        # Act
        await use_case.execute(command=command)

        # Assert
        router_repository.get_routers_page.assert_called_once_with(
            limit=20,
            offset=5,
            sort_by=RouterSortField.NAME,
            sort_order=SortOrder.DESC,
        )
