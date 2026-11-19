from unittest.mock import create_autospec

import pytest

from api.domain.user import UserAuthorization, UserRepository
from api.domain.user.errors import UserCannotReadUserError, UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.admin.users import GetOneUserCommand, GetOneUserUseCase, GetOneUserUseCaseSuccess


@pytest.fixture
def mock_user_repository():
    return create_autospec(UserRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_user_authorization():
    authorization = create_autospec(UserAuthorization, instance=True, spec_set=True)
    authorization.can_read_user.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_user_repository, mock_user_authorization):
    return GetOneUserUseCase(user_repository=mock_user_repository, user_authorization=mock_user_authorization)


@pytest.fixture
def sample_user():
    return UserFactory(id=42)


class TestGetOneUserUseCase:
    @pytest.mark.asyncio
    async def test_should_return_user_when_user_is_admin(self, use_case, mock_user_repository, mock_user_authorization, sample_user):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user

        # Act
        result = await use_case.execute(command=GetOneUserCommand(authenticated_user_id=1, user_id=sample_user.id))

        # Assert
        assert isinstance(result, GetOneUserUseCaseSuccess)
        assert result.user == sample_user
        mock_user_authorization.can_read_user.assert_awaited_once_with(user_id=1, target_user_id=sample_user.id)
        mock_user_repository.get_user_by_id.assert_awaited_once_with(user_id=sample_user.id)

    @pytest.mark.asyncio
    async def test_should_return_user_cannot_read_user_error_without_reading_when_the_user_is_not_allowed(
        self, use_case, mock_user_repository, mock_user_authorization, sample_user
    ):
        # Arrange
        mock_user_authorization.can_read_user.return_value = False

        # Act
        result = await use_case.execute(command=GetOneUserCommand(authenticated_user_id=1, user_id=sample_user.id))

        # Assert
        assert isinstance(result, UserCannotReadUserError)
        assert result.user_id == 1
        mock_user_repository.get_user_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(self, use_case, mock_user_repository):
        # Arrange
        non_existing_user_id = 99
        mock_user_repository.get_user_by_id.return_value = UserNotFoundError(id=non_existing_user_id)

        # Act
        result = await use_case.execute(command=GetOneUserCommand(authenticated_user_id=1, user_id=non_existing_user_id))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == non_existing_user_id
        mock_user_repository.get_user_by_id.assert_awaited_once_with(user_id=non_existing_user_id)
