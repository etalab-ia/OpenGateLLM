from unittest.mock import create_autospec

import pytest

from api.domain import SortField, SortOrder
from api.domain.router import RouterAuthorization, RouterRepository
from api.domain.router.entities import RouterPage
from api.domain.router.errors import UserCannotReadRouterError
from api.tests.unit.use_case.factories import RouterFactory
from api.use_cases.admin.routers import GetRoutersCommand, GetRoutersUseCase, GetRoutersUseCaseSuccess


@pytest.fixture
def mock_router_repository():
    return create_autospec(RouterRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_router_authorization():
    authorization = create_autospec(RouterAuthorization, instance=True, spec_set=True)
    authorization.can_read_router.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_router_repository, mock_router_authorization):
    return GetRoutersUseCase(router_repository=mock_router_repository, router_authorization=mock_router_authorization)


@pytest.fixture
def sample_routers():
    return [RouterFactory(id=1, user_id=1), RouterFactory(id=2, user_id=1)]


@pytest.fixture
def default_command():
    return GetRoutersCommand(authenticated_user_id=1, offset=0, limit=10, sort_by=SortField.ID, sort_order=SortOrder.ASC)


class TestGetRoutersUseCase:
    @pytest.mark.asyncio
    async def test_should_return_routers_page_when_can_read_router_is_allowed(
        self, use_case, mock_router_repository, mock_router_authorization, sample_routers, default_command
    ):
        # Arrange
        mock_router_repository.get_routers_page.return_value = RouterPage(total=2, data=sample_routers)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetRoutersUseCaseSuccess)
        assert result.router_page.data == sample_routers
        assert result.router_page.total == 2
        mock_router_authorization.can_read_router.assert_awaited_once_with(user_id=1)

    @pytest.mark.asyncio
    async def test_should_return_user_cannot_read_router_error_when_can_read_router_is_denied(
        self, use_case, mock_router_repository, mock_router_authorization, default_command
    ):
        # Arrange
        mock_router_authorization.can_read_router.return_value = False

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserCannotReadRouterError)
        assert result.user_id == 1
        mock_router_authorization.can_read_router.assert_awaited_once_with(user_id=1)
        mock_router_repository.get_routers_page.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_forward_pagination_params_to_repository(self, use_case, mock_router_repository, sample_routers):
        # Arrange
        mock_router_repository.get_routers_page.return_value = RouterPage(total=2, data=sample_routers)
        command = GetRoutersCommand(authenticated_user_id=1, offset=5, limit=20, sort_by=SortField.NAME, sort_order=SortOrder.DESC)

        # Act
        await use_case.execute(command=command)

        # Assert
        mock_router_repository.get_routers_page.assert_called_once_with(
            limit=20,
            offset=5,
            sort_by=SortField.NAME,
            sort_order=SortOrder.DESC,
        )
