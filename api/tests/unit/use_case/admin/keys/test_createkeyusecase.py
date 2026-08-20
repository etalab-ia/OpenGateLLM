from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from api.domain.key.entities import Key
from api.domain.key.errors import KeyExpirationInvalidError
from api.domain.user.errors import UserNotFoundError
from api.use_cases.admin.keys import CreateKeyCommand, CreateKeyUseCase, CreateKeyUseCaseSuccess


@pytest.fixture
def key_repository():
    return AsyncMock()


@pytest.fixture
def use_case(key_repository):
    return CreateKeyUseCase(key_repository=key_repository)


@pytest.fixture
def use_case_with_max_expiration(key_repository):
    return CreateKeyUseCase(key_repository=key_repository, key_max_expiration_days=10)


@pytest.fixture
def default_command():
    return CreateKeyCommand(user_id=1, name="my-key", expire=None)


@pytest.fixture
def created_key():
    return Key(
        id=42,
        name="my-key",
        user_id=1,
        value="sk-test-token",
        expires=None,
        created=datetime(2030, 1, 1, tzinfo=UTC),
    )


class TestCreateKeyUseCase:
    @pytest.mark.asyncio
    async def test_should_create_key(self, use_case, key_repository, created_key):
        # Arrange
        command = CreateKeyCommand(user_id=1, name="my-key", expire=None)
        key_repository.create_key.return_value = created_key

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

    @pytest.mark.asyncio
    async def test_should_default_expiration_when_max_days_configured(
        self, use_case_with_max_expiration, key_repository, default_command, created_key
    ):
        # Arrange
        key_repository.create_key.return_value = created_key
        fixed_now = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Act
        with patch("api.use_cases.admin.keys._createkeyusecase.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = fixed_now
            result = await use_case_with_max_expiration.execute(default_command)

        # Assert
        assert isinstance(result, CreateKeyUseCaseSuccess)
        key_repository.create_key.assert_awaited_once_with(user_id=1, name="my-key", expire=fixed_now + timedelta(days=10))

    @pytest.mark.asyncio
    async def test_should_create_key_when_expiration_is_within_max_days(self, use_case_with_max_expiration, key_repository, created_key):
        # Arrange
        expire = datetime(2030, 1, 5, tzinfo=UTC)
        command = CreateKeyCommand(user_id=1, name="my-key", expire=expire)
        key_repository.create_key.return_value = created_key
        fixed_now = datetime(2030, 1, 1, tzinfo=UTC)

        # Act
        with patch("api.use_cases.admin.keys._createkeyusecase.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = fixed_now
            result = await use_case_with_max_expiration.execute(command)

        # Assert
        assert isinstance(result, CreateKeyUseCaseSuccess)
        key_repository.create_key.assert_awaited_once_with(user_id=1, name="my-key", expire=expire)

    @pytest.mark.asyncio
    async def test_should_return_key_expiration_invalid_error_when_expiration_exceeds_max_days(self, use_case_with_max_expiration, key_repository):
        # Arrange
        command = CreateKeyCommand(user_id=1, name="my-key", expire=datetime(2030, 2, 1, tzinfo=UTC))
        fixed_now = datetime(2030, 1, 1, tzinfo=UTC)

        # Act
        with patch("api.use_cases.admin.keys._createkeyusecase.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = fixed_now
            result = await use_case_with_max_expiration.execute(command)

        # Assert
        assert isinstance(result, KeyExpirationInvalidError)
        assert result.max_expiration_days == 10
        key_repository.create_key.assert_not_awaited()
