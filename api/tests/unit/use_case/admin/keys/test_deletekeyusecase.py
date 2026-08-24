from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.use_cases.admin.keys import DeleteKeyCommand, DeleteKeyUseCase, DeleteKeyUseCaseSuccess


@pytest.fixture
def key_repository():
    return AsyncMock()


@pytest.fixture
def use_case(key_repository):
    return DeleteKeyUseCase(key_repository=key_repository)


class TestDeleteKeyUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_key_when_key_exists(self, use_case, key_repository):
        # Arrange
        key = Key(
            id=42,
            name="my-key",
            user_id=1,
            value="sk-masked...value",
            expires=None,
            created=datetime(2030, 1, 1, tzinfo=UTC),
        )
        key_repository.delete_key.return_value = key
        command = DeleteKeyCommand(key_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, DeleteKeyUseCaseSuccess)
        assert result.key == key
        key_repository.delete_key.assert_awaited_once_with(key_id=42, user_id=None)

    @pytest.mark.asyncio
    async def test_should_return_key_not_found_error_when_key_does_not_exist(self, use_case, key_repository):
        # Arrange
        key_repository.delete_key.return_value = KeyNotFoundError(id=99)
        command = DeleteKeyCommand(key_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, KeyNotFoundError)
        assert result.id == 99
        key_repository.delete_key.assert_awaited_once_with(key_id=99, user_id=None)

    @pytest.mark.asyncio
    async def test_should_pass_user_id_to_repository_when_provided(self, use_case, key_repository):
        # Arrange
        key = Key(
            id=42,
            name="my-key",
            user_id=1,
            value="sk-masked...value",
            expires=None,
            created=datetime(2030, 1, 1, tzinfo=UTC),
        )
        key_repository.delete_key.return_value = key
        command = DeleteKeyCommand(key_id=42, user_id=1)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, DeleteKeyUseCaseSuccess)
        assert result.key == key
        key_repository.delete_key.assert_awaited_once_with(key_id=42, user_id=1)
