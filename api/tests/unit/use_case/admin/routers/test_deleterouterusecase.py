from unittest.mock import create_autospec

import pytest

from api.domain.router import RouterAuthorization, RouterRepository
from api.domain.router.errors import RouterNotFoundError, UserCannotDeleteRouterError
from api.tests.unit.use_case.factories import RouterFactory
from api.use_cases.admin.routers import DeleteRouterCommand, DeleteRouterUseCase, DeleteRouterUseCaseSuccess


@pytest.fixture
def mock_router_repository():
    return create_autospec(RouterRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_router_authorization():
    authorization = create_autospec(RouterAuthorization, instance=True, spec_set=True)
    authorization.can_delete_router.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_router_repository, mock_router_authorization):
    return DeleteRouterUseCase(router_repository=mock_router_repository, router_authorization=mock_router_authorization)


@pytest.fixture
def sample_router():
    return RouterFactory(id=42, user_id=1)


class TestDeleteRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_router_when_the_user_is_allowed_and_router_exists(
        self, use_case, mock_router_repository, mock_router_authorization, sample_router
    ):
        # Arrange
        mock_router_repository.delete_router.return_value = sample_router

        # Act
        result = await use_case.execute(command=DeleteRouterCommand(authenticated_user_id=7, router_id=42))

        # Assert
        assert isinstance(result, DeleteRouterUseCaseSuccess)
        assert result.router == sample_router

        mock_router_authorization.can_delete_router.assert_awaited_once_with(user_id=7, router_id=42)
        mock_router_repository.delete_router.assert_awaited_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_an_error_without_deleting_anything_when_the_user_is_not_allowed(
        self, use_case, mock_router_repository, mock_router_authorization
    ):
        # Arrange
        mock_router_authorization.can_delete_router.return_value = False

        # Act
        result = await use_case.execute(command=DeleteRouterCommand(authenticated_user_id=7, router_id=42))

        # Assert
        assert result == UserCannotDeleteRouterError(user_id=7)
        mock_router_repository.delete_router.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, use_case, mock_router_repository):
        # Arrange
        mock_router_repository.delete_router.return_value = RouterNotFoundError(id=99)

        # Act
        result = await use_case.execute(command=DeleteRouterCommand(authenticated_user_id=7, router_id=99))

        # Assert
        assert result == RouterNotFoundError(id=99)
        mock_router_repository.delete_router.assert_awaited_once_with(99)
