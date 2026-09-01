from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from api.domain.key.entities import Key, KeyStatus
from api.domain.key.errors import KeyNotFoundError
from api.use_cases.admin.keys import GetOneKeyCommand, GetOneKeyUseCase, GetOneKeyUseCaseSuccess


@pytest.fixture
def key_repository():
    return AsyncMock()


@pytest.fixture
def use_case(key_repository):
    return GetOneKeyUseCase(key_repository=key_repository)


@pytest.fixture
def key():
    return Key(
        id=42,
        name="my-key",
        user_id=1,
        value="sk-masked...value",
        expires=None,
        created=datetime(2030, 1, 1, tzinfo=UTC),
    )


class TestGetOneKeyUseCase:
    @pytest.mark.asyncio
    async def test_should_return_key_when_key_exists(self, use_case, key_repository, key):
        # Arrange
        key_repository.get_key_by_id.return_value = key
        command = GetOneKeyCommand(key_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetOneKeyUseCaseSuccess)
        assert result.key.status == KeyStatus.ACTIVE
        key_repository.get_key_by_id.assert_awaited_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_key_when_user_id_matches_owner(self, use_case, key_repository, key):
        # Arrange
        key_repository.get_key_by_id.return_value = key
        command = GetOneKeyCommand(key_id=42, user_id=1)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetOneKeyUseCaseSuccess)
        assert result.key.status == KeyStatus.ACTIVE
        key_repository.get_key_by_id.assert_awaited_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_key_not_found_error_when_key_does_not_exist(self, use_case, key_repository):
        # Arrange
        key_repository.get_key_by_id.return_value = KeyNotFoundError(id=99)
        command = GetOneKeyCommand(key_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, KeyNotFoundError)
        assert result.id == 99
        key_repository.get_key_by_id.assert_awaited_once_with(99)

    @pytest.mark.asyncio
    async def test_should_return_key_not_found_error_when_user_id_does_not_match_owner(self, use_case, key_repository, key):
        # Arrange
        key_repository.get_key_by_id.return_value = key
        command = GetOneKeyCommand(key_id=42, user_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, KeyNotFoundError)
        assert result.id == 42
        key_repository.get_key_by_id.assert_awaited_once_with(42)
