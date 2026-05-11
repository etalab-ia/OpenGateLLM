import time
from unittest.mock import AsyncMock, Mock, patch

from fastapi.security import HTTPAuthorizationCredentials
import pytest

from api.domain.key.entities import KeyClaims
from api.domain.key.errors import KeyNotFoundError
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.endpoints.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException


@pytest.fixture
def key_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def request_context() -> Mock:
    context = Mock()
    context.get.return_value = Mock(user_id=None, key_id=None)
    return context


@pytest.fixture
def api_key() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="sk-token")


@pytest.fixture
def request_obj() -> Mock:
    return Mock()


class TestGetCurrentKey:
    @pytest.mark.asyncio
    async def test_should_raise_invalid_authentication_scheme_when_scheme_is_not_bearer(
        self, request_obj: Mock, key_repository: AsyncMock, request_context: Mock
    ):
        # Arrange
        api_key = HTTPAuthorizationCredentials(scheme="Basic", credentials="sk-token")

        # Act / Assert
        with pytest.raises(InvalidAuthenticationSchemeException):
            await get_current_key(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                secret_key="secret",
                request_context=request_context,
            )

        key_repository.get_key_expiration.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_raise_invalid_api_key_when_credentials_are_empty(
        self, request_obj: Mock, key_repository: AsyncMock, request_context: Mock
    ):
        # Arrange
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

        # Act / Assert
        with pytest.raises(InvalidAPIKeyException):
            await get_current_key(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                secret_key="secret",
                request_context=request_context,
            )

        key_repository.get_key_expiration.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_raise_invalid_api_key_when_key_not_found_in_repository(
        self, request_obj: Mock, api_key: HTTPAuthorizationCredentials, key_repository: AsyncMock, request_context: Mock
    ):
        # Arrange
        key_repository.get_key_expiration.return_value = KeyNotFoundError()

        # Act / Assert
        with patch("api.infrastructure.fastapi.access.Key.decode", return_value=KeyClaims(user_id=1, key_id=10)):
            with pytest.raises(InvalidAPIKeyException):
                await get_current_key(
                    request=request_obj,
                    api_key=api_key,
                    key_repository=key_repository,
                    secret_key="secret",
                    request_context=request_context,
                )

        key_repository.get_key_expiration.assert_awaited_once_with(user_id=1, key_id=10)

    @pytest.mark.asyncio
    async def test_should_raise_invalid_api_key_when_key_is_expired(
        self, request_obj: Mock, api_key: HTTPAuthorizationCredentials, key_repository: AsyncMock, request_context: Mock
    ):
        # Arrange
        expired_timestamp = int(time.time()) - 1000
        key_repository.get_key_expiration.return_value = expired_timestamp

        # Act / Assert
        with patch("api.infrastructure.fastapi.access.Key.decode", return_value=KeyClaims(user_id=1, key_id=10)):
            with pytest.raises(InvalidAPIKeyException):
                await get_current_key(
                    request=request_obj,
                    api_key=api_key,
                    key_repository=key_repository,
                    secret_key="secret",
                    request_context=request_context,
                )

    @pytest.mark.asyncio
    async def test_should_set_user_id_and_key_id_in_request_context_when_key_is_valid(
        self, request_obj: Mock, api_key: HTTPAuthorizationCredentials, key_repository: AsyncMock, request_context: Mock
    ):
        # Arrange
        future_timestamp = int(time.time()) + 1000
        key_repository.get_key_expiration.return_value = future_timestamp

        # Act
        with patch("api.infrastructure.fastapi.access.Key.decode", return_value=KeyClaims(user_id=42, key_id=99)):
            await get_current_key(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                secret_key="secret",
                request_context=request_context,
            )

        # Assert
        assert request_context.get().user_id == 42
        assert request_context.get().key_id == 99
        key_repository.get_key_expiration.assert_awaited_once_with(user_id=42, key_id=99)
