from unittest.mock import AsyncMock

import pytest

from api.domain.router.errors import RouterNotFoundError
from api.tests.unit.use_case.factories import RouterFactory
from api.use_cases.admin.routers import GetOneRouterCommand, GetOneRouterUseCase, GetOneRouterUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository):
    return GetOneRouterUseCase(router_repository=router_repository)


@pytest.fixture
def sample_router():
    return RouterFactory(id=42, user_id=1)


class TestGetOneRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_return_router_when_user_is_admin(self, use_case, router_repository, sample_router):
        # Arrange
        use_case.router_repository.get_router_by_id.return_value = sample_router

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(router_id=42))

        # Assert
        assert isinstance(result, GetOneRouterUseCaseSuccess)
        assert result.router == sample_router

        router_repository.get_router_by_id.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, router_repository, use_case):
        # Arrange
        use_case.router_repository.get_router_by_id.return_value = None

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(router_id=99))

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 99
        router_repository.get_router_by_id.assert_called_once_with(99)
