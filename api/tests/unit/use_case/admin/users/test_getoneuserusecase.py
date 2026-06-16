from unittest.mock import AsyncMock

import pytest

from api.domain.user.errors import UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.admin.users import GetOneUserCommand, GetOneUserUseCase, GetOneUserUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository):
    return GetOneUserUseCase(user_repository=user_repository)


@pytest.fixture
def sample_user():
    return UserFactory(id=42)


class TestGetOneUserUseCase:
    @pytest.mark.asyncio
    async def test_should_return_user_when_user_is_admin(self, use_case, user_repository, sample_user):
        # Arrange

        use_case.user_repository.get_user_by_id.return_value = sample_user

        # Act
        result = await use_case.execute(command=GetOneUserCommand(user_id=sample_user.id))

        # Assert
        assert isinstance(result, GetOneUserUseCaseSuccess)
        assert result.user == sample_user

        user_repository.get_user_by_id.assert_called_once_with(user_id=sample_user.id)

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(self, use_case, user_repository):
        # Arrange

        non_existing_user_id = 99
        use_case.user_repository.get_user_by_id.return_value = UserNotFoundError(id=non_existing_user_id)

        # Act
        result = await use_case.execute(command=GetOneUserCommand(user_id=non_existing_user_id))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == non_existing_user_id
        user_repository.get_user_by_id.assert_called_once_with(user_id=non_existing_user_id)
