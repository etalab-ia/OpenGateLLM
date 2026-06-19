from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.domain.key.entities import Key
from api.domain.user.errors import InvalidUserPasswordError, UserNotFoundError
from api.use_cases.auth import AuthLoginCommand, AuthLoginUseCase, AuthLoginUseCaseSuccess


@pytest.fixture
def key_repository():
    return AsyncMock()


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def user_password_encoder():
    encoder = MagicMock()
    encoder.validate_password.return_value = True
    return encoder


@pytest.fixture
def use_case(key_repository, user_repository, user_password_encoder):
    return AuthLoginUseCase(
        key_repository=key_repository,
        user_repository=user_repository,
        user_password_encoder=user_password_encoder,
        login_session_duration=3600,
    )


@pytest.fixture
def default_command():
    return AuthLoginCommand(email="user@test.com", password="s3cr3t")


class TestAuthLoginUseCase:
    @pytest.mark.asyncio
    async def test_should_refresh_playground_key_when_credentials_are_valid(
        self, use_case, key_repository, user_repository, user_password_encoder, default_command
    ):
        # Arrange
        user_repository.get_user_id_and_password_by_email.return_value = (1, "encoded:s3cr3t")
        refreshed_key = Key(
            id=42,
            name="playground",
            user_id=1,
            value="sk-test-token",
            expires=datetime(2030, 1, 1, tzinfo=UTC),
            created=datetime(2030, 1, 1, tzinfo=UTC),
        )
        key_repository.upsert_key.return_value = refreshed_key

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, AuthLoginUseCaseSuccess)
        assert result.key.id == 42
        assert result.key.name == "playground"
        user_repository.get_user_id_and_password_by_email.assert_awaited_once_with(email="user@test.com")
        user_password_encoder.validate_password.assert_called_once_with(password="s3cr3t", encoded_password="encoded:s3cr3t")
        key_repository.upsert_key.assert_awaited_once()
        assert key_repository.upsert_key.await_args.kwargs["user_id"] == 1
        assert key_repository.upsert_key.await_args.kwargs["name"] == "playground"
        assert key_repository.upsert_key.await_args.kwargs["expire"] is not None

    @pytest.mark.asyncio
    async def test_should_refresh_playground_key_when_password_is_null(self, use_case, key_repository, user_repository, user_password_encoder):
        # Arrange
        command = AuthLoginCommand(email="user@test.com", password=None)
        user_repository.get_user_id_and_password_by_email.return_value = (1, None)
        refreshed_key = Key(
            id=42,
            name="playground",
            user_id=1,
            value="sk-test-token",
            expires=datetime(2030, 1, 1, tzinfo=UTC),
            created=datetime(2030, 1, 1, tzinfo=UTC),
        )
        key_repository.upsert_key.return_value = refreshed_key

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, AuthLoginUseCaseSuccess)
        assert result.key.id == 42
        assert result.key.name == "playground"
        user_repository.get_user_id_and_password_by_email.assert_awaited_once_with(email="user@test.com")
        user_password_encoder.validate_password.assert_not_called()
        key_repository.upsert_key.assert_awaited_once()
        assert key_repository.upsert_key.await_args.kwargs["user_id"] == 1
        assert key_repository.upsert_key.await_args.kwargs["name"] == "playground"
        assert key_repository.upsert_key.await_args.kwargs["expire"] is not None

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error(self, use_case, user_repository, default_command):
        # Arrange
        user_repository.get_user_id_and_password_by_email.return_value = UserNotFoundError(email="user@test.com")

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.email == "user@test.com"

    @pytest.mark.asyncio
    async def test_should_return_invalid_user_password_error(self, use_case, user_repository, user_password_encoder, default_command):
        # Arrange
        user_repository.get_user_id_and_password_by_email.return_value = (1, "encoded:s3cr3t")
        user_password_encoder.validate_password.return_value = False

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, InvalidUserPasswordError)
