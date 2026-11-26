from unittest.mock import create_autospec

import pytest

from api.domain.router import RouterAuthorization, RouterRepository
from api.domain.router.errors import RouterNotFoundError, UserCannotReadRouterError
from api.tests.unit.use_case.factories import RouterFactory
from api.use_cases.admin.routers import GetOneRouterCommand, GetOneRouterUseCase, GetOneRouterUseCaseSuccess


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
    return GetOneRouterUseCase(router_repository=mock_router_repository, router_authorization=mock_router_authorization)


@pytest.fixture
def sample_router():
    return RouterFactory(id=42, user_id=1)


class TestGetOneRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_return_router_when_can_read_router_is_allowed(
        self, use_case, mock_router_repository, mock_router_authorization, sample_router
    ):
        # Arrange
        mock_router_repository.get_router_by_id.return_value = sample_router

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(authenticated_user_id=1, router_id=42))

        # Assert
        assert isinstance(result, GetOneRouterUseCaseSuccess)
        assert result.router == sample_router
        mock_router_authorization.can_read_router.assert_awaited_once_with(user_id=1)
        mock_router_repository.get_router_by_id.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_user_cannot_read_router_error_when_can_read_router_is_denied(
        self, use_case, mock_router_repository, mock_router_authorization, sample_router
    ):
        # Arrange
        mock_router_authorization.can_read_router.return_value = False

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(authenticated_user_id=1, router_id=sample_router.id))

        # Assert
        assert isinstance(result, UserCannotReadRouterError)
        assert result.user_id == 1
        mock_router_authorization.can_read_router.assert_awaited_once_with(user_id=1)
        mock_router_repository.get_router_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, use_case, mock_router_repository):
        # Arrange
        mock_router_repository.get_router_by_id.return_value = None

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(authenticated_user_id=1, router_id=99))

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 99
        mock_router_repository.get_router_by_id.assert_called_once_with(99)
