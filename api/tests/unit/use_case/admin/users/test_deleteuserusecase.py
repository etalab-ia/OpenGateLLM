from unittest.mock import AsyncMock

import pytest

from api.domain.user.errors import DeleteUserWithProvidersError, DeleteUserWithRoutersError, UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.admin.users import DeleteUserCommand, DeleteUserUseCase, DeleteUserUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository, router_repository, provider_repository):
    return DeleteUserUseCase(
        user_repository=user_repository,
        router_repository=router_repository,
        provider_repository=provider_repository,
    )


@pytest.fixture
def sample_user():
    return UserFactory(id=42)


class TestDeleteUserUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_user_when_admin_and_user_exists(
        self, use_case, user_repository, router_repository, provider_repository, sample_user
    ):
        # Arrange

        user_repository.delete_user.return_value = sample_user

        # Act
        result = await use_case.execute(DeleteUserCommand(user_id=sample_user.id))

        # Assert
        assert isinstance(result, DeleteUserUseCaseSuccess)
        assert result.user == sample_user

        user_repository.delete_user.assert_called_once_with(user_id=sample_user.id)

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(
        self, use_case, user_repository, router_repository, provider_repository
    ):
        # Arrange

        user_repository.delete_user.return_value = UserNotFoundError(id=99)

        # Act
        result = await use_case.execute(DeleteUserCommand(user_id=99))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 99
        user_repository.delete_user.assert_called_once_with(user_id=99)

    @pytest.mark.asyncio
    async def test_should_return_delete_user_with_routers_error_with_ids_when_user_has_routers(
        self, use_case, user_repository, router_repository, provider_repository
    ):
        # Arrange

        user_repository.delete_user.return_value = DeleteUserWithRoutersError(user_id=42, router_ids=None)
        router_repository.get_router_ids_by_user_id.return_value = [1, 2, 3]

        # Act
        result = await use_case.execute(DeleteUserCommand(user_id=42))

        # Assert
        assert isinstance(result, DeleteUserWithRoutersError)
        assert result.router_ids == [1, 2, 3]
        user_repository.delete_user.assert_called_once_with(user_id=42)
        router_repository.get_router_ids_by_user_id.assert_called_once_with(user_id=42)
        provider_repository.get_provider_ids_by_user_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_delete_user_with_providers_error_with_ids_when_user_has_providers(
        self, use_case, user_repository, router_repository, provider_repository
    ):
        # Arrange

        user_repository.delete_user.return_value = DeleteUserWithProvidersError(user_id=42, provider_ids=None)
        provider_repository.get_provider_ids_by_user_id.return_value = [10, 20]

        # Act
        result = await use_case.execute(DeleteUserCommand(user_id=42))

        # Assert
        assert isinstance(result, DeleteUserWithProvidersError)
        assert result.provider_ids == [10, 20]
        user_repository.delete_user.assert_called_once_with(user_id=42)
        provider_repository.get_provider_ids_by_user_id.assert_called_once_with(user_id=42)
        router_repository.get_router_ids_by_user_id.assert_not_called()
