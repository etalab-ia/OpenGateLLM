from unittest.mock import AsyncMock

import pytest

from api.domain import SortField, SortOrder
from api.domain.router.entities import RouterPage
from api.tests.unit.use_case.factories import RouterFactory
from api.use_cases.admin.routers import GetRoutersCommand, GetRoutersUseCase, GetRoutersUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository):
    return GetRoutersUseCase(router_repository=router_repository)


@pytest.fixture
def sample_routers():
    return [RouterFactory(id=1, user_id=1), RouterFactory(id=2, user_id=1)]


@pytest.fixture
def default_command():
    return GetRoutersCommand(offset=0, limit=10, sort_by=SortField.ID, sort_order=SortOrder.ASC)


class TestGetRoutersUseCase:
    @pytest.mark.asyncio
    async def test_should_return_routers_when_user_is_admin(self, use_case, router_repository, sample_routers, default_command):
        # Arrange
        use_case.router_repository.get_routers_page.return_value = RouterPage(total=2, data=sample_routers)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetRoutersUseCaseSuccess)
        assert result.router_page.data == sample_routers
        assert result.router_page.total == 2

    @pytest.mark.asyncio
    async def test_should_forward_pagination_params_to_repository(self, use_case, router_repository, sample_routers):
        # Arrange
        use_case.router_repository.get_routers_page.return_value = RouterPage(total=2, data=sample_routers)
        command = GetRoutersCommand(offset=5, limit=20, sort_by=SortField.NAME, sort_order=SortOrder.DESC)

        # Act
        await use_case.execute(command=command)

        # Assert
        router_repository.get_routers_page.assert_called_once_with(
            limit=20,
            offset=5,
            sort_by=SortField.NAME,
            sort_order=SortOrder.DESC,
        )
