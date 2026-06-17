from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from api.domain.key.entities import Key
from api.domain.user.errors import UserNotFoundError
from api.use_cases.admin.keys import CreateKeyCommand, CreateKeyUseCase, CreateKeyUseCaseSuccess


@pytest.fixture
def key_repository():
    return AsyncMock()


@pytest.fixture
def use_case(key_repository):
    return CreateKeyUseCase(key_repository=key_repository)


@pytest.fixture
def default_command():
    return CreateKeyCommand(user_id=1, name="my-key", expire=None)


class TestCreateKeyUseCase:
    @pytest.mark.asyncio
    async def test_should_create_key(self, use_case, key_repository):
        # Arrange
        command = CreateKeyCommand(user_id=1, name="my-key", expire=None)
        created = Key(
            id=42,
            name="my-key",
            user_id=1,
            value="sk-test-token",
            expires=None,
            created=datetime(2030, 1, 1, tzinfo=UTC),
        )
        key_repository.create_key.return_value = created

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, CreateKeyUseCaseSuccess)
        assert result.key.id == 42
        assert result.key.name == "my-key"
        key_repository.create_key.assert_awaited_once_with(user_id=1, name="my-key", expire=None)

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error(self, use_case, key_repository, default_command):
        # Arrange
        key_repository.create_key.return_value = UserNotFoundError(id=1)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 1
