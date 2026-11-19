from unittest.mock import create_autospec

import pytest

from api.domain.user import UserAuthorization, UserRepository
from api.domain.user.errors import UserCannotDeleteUserError, UserHasProvidersError, UserHasRoutersError, UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.admin.users import DeleteUserCommand, DeleteUserUseCase, DeleteUserUseCaseSuccess


@pytest.fixture
def mock_user_repository():
    return create_autospec(UserRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_user_authorization():
    authorization = create_autospec(UserAuthorization, instance=True, spec_set=True)
    authorization.can_delete_user.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_user_repository, mock_user_authorization):
    return DeleteUserUseCase(user_repository=mock_user_repository, user_authorization=mock_user_authorization)


@pytest.fixture
def sample_user():
    return UserFactory(id=42)


class TestDeleteUserUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_user_when_admin_and_user_exists(self, use_case, mock_user_repository, mock_user_authorization, sample_user):
        # Arrange
        mock_user_repository.delete_user.return_value = sample_user

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=1, user_id=sample_user.id))

        # Assert
        assert isinstance(result, DeleteUserUseCaseSuccess)
        assert result.user == sample_user

        mock_user_authorization.can_delete_user.assert_awaited_once_with(user_id=1, target_user_id=sample_user.id)
        mock_user_repository.delete_user.assert_awaited_once_with(user_id=sample_user.id)

    @pytest.mark.asyncio
    async def test_should_return_user_cannot_delete_user_error_without_deleting_when_the_user_is_not_allowed(
        self, use_case, mock_user_repository, mock_user_authorization
    ):
        # Arrange
        mock_user_authorization.can_delete_user.return_value = False

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=1, user_id=42))

        # Assert
        assert isinstance(result, UserCannotDeleteUserError)
        assert result.user_id == 1
        mock_user_authorization.can_delete_user.assert_awaited_once_with(user_id=1, target_user_id=42)
        mock_user_repository.delete_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(self, use_case, mock_user_repository):
        # Arrange
        mock_user_repository.delete_user.return_value = UserNotFoundError(id=99)

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=1, user_id=99))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 99
        mock_user_repository.delete_user.assert_awaited_once_with(user_id=99)

    @pytest.mark.asyncio
    async def test_should_return_user_has_routers_error_when_user_has_routers(self, use_case, mock_user_repository):
        # Arrange
        mock_user_repository.delete_user.return_value = UserHasRoutersError(id=42)

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=1, user_id=42))

        # Assert
        assert isinstance(result, UserHasRoutersError)
        assert result.id == 42
        mock_user_repository.delete_user.assert_awaited_once_with(user_id=42)

    @pytest.mark.asyncio
    async def test_should_return_user_has_providers_error_when_user_has_providers(self, use_case, mock_user_repository):
        # Arrange
        mock_user_repository.delete_user.return_value = UserHasProvidersError(id=42)

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=1, user_id=42))

        # Assert
        assert isinstance(result, UserHasProvidersError)
        assert result.id == 42
        mock_user_repository.delete_user.assert_awaited_once_with(user_id=42)
