from unittest.mock import AsyncMock

import pytest

from api.domain.router.errors import RouterNotFoundError
from api.tests.unit.use_case.factories import RouterFactory
from api.use_cases.admin.routers import DeleteRouterCommand, DeleteRouterUseCase, DeleteRouterUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository):
    return DeleteRouterUseCase(router_repository=router_repository)


@pytest.fixture
def sample_router():
    return RouterFactory(id=42, user_id=1)


class TestDeleteRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_router_when_user_is_admin_and_router_exists(self, use_case, router_repository, sample_router):
        # Arrange

        use_case.router_repository.delete_router.return_value = sample_router

        # Act
        result = await use_case.execute(command=DeleteRouterCommand(router_id=42))

        # Assert
        assert isinstance(result, DeleteRouterUseCaseSuccess)
        assert result.router == sample_router

        router_repository.delete_router.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, use_case, router_repository):
        # Arrange

        use_case.router_repository.delete_router.return_value = RouterNotFoundError(id=99)

        # Act
        result = await use_case.execute(command=DeleteRouterCommand(router_id=99))

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 99
        router_repository.delete_router.assert_called_once_with(99)
