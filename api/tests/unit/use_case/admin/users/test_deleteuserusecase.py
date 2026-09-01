from unittest.mock import AsyncMock

import pytest

from api.domain.user.errors import UserHasProvidersError, UserHasRoutersError, UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.admin.users import DeleteUserCommand, DeleteUserUseCase, DeleteUserUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository):
    return DeleteUserUseCase(user_repository=user_repository)


@pytest.fixture
def sample_user():
    return UserFactory(id=42)


class TestDeleteUserUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_user_when_admin_and_user_exists(self, use_case, user_repository, sample_user):
        # Arrange

        user_repository.delete_user.return_value = sample_user

        # Act
        result = await use_case.execute(DeleteUserCommand(user_id=sample_user.id))

        # Assert
        assert isinstance(result, DeleteUserUseCaseSuccess)
        assert result.user == sample_user

        user_repository.delete_user.assert_called_once_with(user_id=sample_user.id)

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(self, use_case, user_repository):
        # Arrange

        user_repository.delete_user.return_value = UserNotFoundError(id=99)

        # Act
        result = await use_case.execute(DeleteUserCommand(user_id=99))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 99
        user_repository.delete_user.assert_called_once_with(user_id=99)

    @pytest.mark.asyncio
    async def test_should_return_user_has_routers_error_when_user_has_routers(self, use_case, user_repository):
        # Arrange

        user_repository.delete_user.return_value = UserHasRoutersError(id=42)

        # Act
        result = await use_case.execute(DeleteUserCommand(user_id=42))

        # Assert
        assert isinstance(result, UserHasRoutersError)
        assert result.id == 42
        user_repository.delete_user.assert_called_once_with(user_id=42)

    @pytest.mark.asyncio
    async def test_should_return_user_has_providers_error_when_user_has_providers(self, use_case, user_repository):
        # Arrange

        user_repository.delete_user.return_value = UserHasProvidersError(id=42)

        # Act
        result = await use_case.execute(DeleteUserCommand(user_id=42))

        # Assert
        assert isinstance(result, UserHasProvidersError)
        assert result.id == 42
        user_repository.delete_user.assert_called_once_with(user_id=42)
