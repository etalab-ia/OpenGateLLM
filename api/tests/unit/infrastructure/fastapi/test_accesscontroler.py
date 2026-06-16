from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from fastapi.security import HTTPAuthorizationCredentials
import pytest

from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.domain.role.entities import PermissionType
from api.infrastructure.fastapi._accesscontroler import AccessController
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.endpoints.exceptions import (
    AccountExpiredHTTPException,
    InvalidAPIKeyHTTPException,
    InvalidAuthenticationSchemeHTTPException,
    NotAdminUserHTTPException,
)
from api.tests.unit.use_case.factories import UserWithRoleFactory


@pytest.fixture
def access_controller() -> AccessController:
    return AccessController()


@pytest.fixture
def admin_access_controller() -> AccessController:
    return AccessController(only_admin=True)


@pytest.fixture
def key_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def user_with_role_query() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def request_context() -> ContextVar[RequestContext]:
    context = ContextVar("request_context", default=RequestContext())
    context.set(RequestContext())
    return context


@pytest.fixture
def api_key() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="sk-jwt-token")


@pytest.fixture
def request_obj() -> Mock:
    return Mock()


@pytest.fixture
def decoded_key() -> Key:
    return Key(id=99, name="dev", user_id=42, expires=None, created=datetime.now(UTC))


@pytest.fixture
def stored_key(decoded_key: Key) -> Key:
    return decoded_key.model_copy()


class TestAccessController:
    @pytest.mark.asyncio
    async def test_should_raise_invalid_authentication_scheme_when_scheme_is_not_bearer(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: AsyncMock,
        user_with_role_query: AsyncMock,
        request_context: ContextVar[RequestContext],
    ):
        # Arrange
        api_key = HTTPAuthorizationCredentials(scheme="Basic", credentials="sk-jwt-token")

        # Act / Assert
        with pytest.raises(InvalidAuthenticationSchemeHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                secret_key="secret",
                key_repository=key_repository,
                user_with_role_query=user_with_role_query,
                request_context=request_context,
            )

        key_repository.get_key_by_id.assert_not_awaited()
        user_with_role_query.get_user_with_role_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_raise_invalid_api_key_when_credentials_are_empty(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: AsyncMock,
        user_with_role_query: AsyncMock,
        request_context: ContextVar[RequestContext],
    ):
        # Arrange
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                secret_key="secret",
                key_repository=key_repository,
                user_with_role_query=user_with_role_query,
                request_context=request_context,
            )

        key_repository.get_key_by_id.assert_not_awaited()
        user_with_role_query.get_user_with_role_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_raise_invalid_api_key_when_credentials_do_not_have_sk_prefix(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: AsyncMock,
        user_with_role_query: AsyncMock,
        request_context: ContextVar[RequestContext],
    ):
        # Arrange
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials="jwt-token")

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                secret_key="secret",
                key_repository=key_repository,
                user_with_role_query=user_with_role_query,
                request_context=request_context,
            )

        key_repository.get_key_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_raise_invalid_api_key_when_jwt_decode_fails(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        api_key: HTTPAuthorizationCredentials,
        key_repository: AsyncMock,
        user_with_role_query: AsyncMock,
        request_context: ContextVar[RequestContext],
    ):
        # Arrange
        with patch("api.infrastructure.fastapi._accesscontroler.jwt.decode", side_effect=ValueError("invalid token")):
            # Act / Assert
            with pytest.raises(InvalidAPIKeyHTTPException):
                await access_controller(
                    request=request_obj,
                    api_key=api_key,
                    secret_key="secret",
                    key_repository=key_repository,
                    user_with_role_query=user_with_role_query,
                    request_context=request_context,
                )

        key_repository.get_key_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_raise_invalid_api_key_when_key_not_found_in_repository(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        api_key: HTTPAuthorizationCredentials,
        decoded_key: Key,
        key_repository: AsyncMock,
        user_with_role_query: AsyncMock,
        request_context: ContextVar[RequestContext],
    ):
        # Arrange
        key_repository.get_key_by_id.return_value = KeyNotFoundError(id=99)

        with patch("api.infrastructure.fastapi._accesscontroler.jwt.decode", return_value={"token_id": 99, "user_id": 42, "expires": None}):
            with patch("api.infrastructure.fastapi._accesscontroler.Key.build_from_claims", return_value=decoded_key):
                # Act / Assert
                with pytest.raises(InvalidAPIKeyHTTPException):
                    await access_controller(
                        request=request_obj,
                        api_key=api_key,
                        secret_key="secret",
                        key_repository=key_repository,
                        user_with_role_query=user_with_role_query,
                        request_context=request_context,
                    )

        key_repository.get_key_by_id.assert_awaited_once_with(key_id=99)
        user_with_role_query.get_user_with_role_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_raise_invalid_api_key_when_key_does_not_match_stored_key(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        api_key: HTTPAuthorizationCredentials,
        decoded_key: Key,
        key_repository: AsyncMock,
        user_with_role_query: AsyncMock,
        request_context: ContextVar[RequestContext],
    ):
        # Arrange
        stored_key = decoded_key.model_copy(update={"expires": datetime.now(UTC) + timedelta(days=1)})
        key_repository.get_key_by_id.return_value = stored_key

        with patch("api.infrastructure.fastapi._accesscontroler.jwt.decode", return_value={"token_id": 99, "user_id": 42, "expires": None}):
            with patch("api.infrastructure.fastapi._accesscontroler.Key.build_from_claims", return_value=decoded_key):
                # Act / Assert
                with pytest.raises(InvalidAPIKeyHTTPException):
                    await access_controller(
                        request=request_obj,
                        api_key=api_key,
                        secret_key="secret",
                        key_repository=key_repository,
                        user_with_role_query=user_with_role_query,
                        request_context=request_context,
                    )

        key_repository.get_key_by_id.assert_awaited_once_with(key_id=99)
        user_with_role_query.get_user_with_role_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_raise_account_expired_when_user_has_expired(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        api_key: HTTPAuthorizationCredentials,
        decoded_key: Key,
        stored_key: Key,
        key_repository: AsyncMock,
        user_with_role_query: AsyncMock,
        request_context: ContextVar[RequestContext],
    ):
        # Arrange
        key_repository.get_key_by_id.return_value = stored_key
        user_with_role_query.get_user_with_role_by_id.return_value = UserWithRoleFactory(
            id=42,
            expires=int((datetime.now(UTC) - timedelta(days=1)).timestamp()),
        )

        with patch("api.infrastructure.fastapi._accesscontroler.jwt.decode", return_value={"token_id": 99, "user_id": 42, "expires": None}):
            with patch("api.infrastructure.fastapi._accesscontroler.Key.build_from_claims", return_value=decoded_key):
                # Act / Assert
                with pytest.raises(AccountExpiredHTTPException):
                    await access_controller(
                        request=request_obj,
                        api_key=api_key,
                        secret_key="secret",
                        key_repository=key_repository,
                        user_with_role_query=user_with_role_query,
                        request_context=request_context,
                    )

        user_with_role_query.get_user_with_role_by_id.assert_awaited_once_with(user_id=42)

    @pytest.mark.asyncio
    async def test_should_raise_not_admin_user_when_only_admin_is_required(
        self,
        admin_access_controller: AccessController,
        request_obj: Mock,
        api_key: HTTPAuthorizationCredentials,
        decoded_key: Key,
        stored_key: Key,
        key_repository: AsyncMock,
        user_with_role_query: AsyncMock,
        request_context: ContextVar[RequestContext],
    ):
        # Arrange
        key_repository.get_key_by_id.return_value = stored_key
        user_with_role_query.get_user_with_role_by_id.return_value = UserWithRoleFactory(
            id=42,
            permissions=[PermissionType.READ_METRIC],
            no_expiration=True,
        )

        with patch("api.infrastructure.fastapi._accesscontroler.jwt.decode", return_value={"token_id": 99, "user_id": 42, "expires": None}):
            with patch("api.infrastructure.fastapi._accesscontroler.Key.build_from_claims", return_value=decoded_key):
                # Act / Assert
                with pytest.raises(NotAdminUserHTTPException):
                    await admin_access_controller(
                        request=request_obj,
                        api_key=api_key,
                        secret_key="secret",
                        key_repository=key_repository,
                        user_with_role_query=user_with_role_query,
                        request_context=request_context,
                    )

    @pytest.mark.asyncio
    async def test_should_set_key_and_user_in_request_context_when_access_is_valid(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        api_key: HTTPAuthorizationCredentials,
        decoded_key: Key,
        stored_key: Key,
        key_repository: AsyncMock,
        user_with_role_query: AsyncMock,
        request_context: ContextVar[RequestContext],
    ):
        # Arrange
        user = UserWithRoleFactory(id=42, no_expiration=True)
        key_repository.get_key_by_id.return_value = stored_key
        user_with_role_query.get_user_with_role_by_id.return_value = user

        with patch("api.infrastructure.fastapi._accesscontroler.jwt.decode", return_value={"token_id": 99, "user_id": 42, "expires": None}):
            with patch("api.infrastructure.fastapi._accesscontroler.Key.build_from_claims", return_value=decoded_key):
                # Act
                await access_controller(
                    request=request_obj,
                    api_key=api_key,
                    secret_key="secret",
                    key_repository=key_repository,
                    user_with_role_query=user_with_role_query,
                    request_context=request_context,
                )

        # Assert
        assert request_context.get().key == decoded_key
        assert request_context.get().user == user
        key_repository.get_key_by_id.assert_awaited_once_with(key_id=99)
        user_with_role_query.get_user_with_role_by_id.assert_awaited_once_with(user_id=42)

    @pytest.mark.asyncio
    async def test_should_allow_admin_user_when_only_admin_is_required(
        self,
        admin_access_controller: AccessController,
        request_obj: Mock,
        api_key: HTTPAuthorizationCredentials,
        decoded_key: Key,
        stored_key: Key,
        key_repository: AsyncMock,
        user_with_role_query: AsyncMock,
        request_context: ContextVar[RequestContext],
    ):
        # Arrange
        user = UserWithRoleFactory(id=42, admin=True, no_expiration=True)
        key_repository.get_key_by_id.return_value = stored_key
        user_with_role_query.get_user_with_role_by_id.return_value = user

        with patch("api.infrastructure.fastapi._accesscontroler.jwt.decode", return_value={"token_id": 99, "user_id": 42, "expires": None}):
            with patch("api.infrastructure.fastapi._accesscontroler.Key.build_from_claims", return_value=decoded_key):
                # Act
                await admin_access_controller(
                    request=request_obj,
                    api_key=api_key,
                    secret_key="secret",
                    key_repository=key_repository,
                    user_with_role_query=user_with_role_query,
                    request_context=request_context,
                )

        # Assert
        assert request_context.get().key == decoded_key
        assert request_context.get().user == user
