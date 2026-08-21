from contextvars import ContextVar, Token
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
import pytest

from api.domain.role.entities import PermissionType
from api.infrastructure.fastapi import RequestContext
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.fastapi.endpoints.exceptions import (
    AccountExpiredHTTPException,
    InvalidAPIKeyHTTPException,
    InvalidAuthenticationSchemeHTTPException,
    NotAdminUserHTTPException,
)
from api.infrastructure.jwt import JwtKeyEncoder
from api.infrastructure.postgres import PostgresAuthenticatedUserQuery, PostgresKeyRepository
from api.tests.helpers import create_key
from api.tests.integration.factories.sql import KeySQLFactory, PermissionSQLFactory, RoleSQLFactory, UserSQLFactory


def _encode_api_key(
    *,
    secret_key: str,
    user_id: int | None,
    token_id: int | None,
    expires: int | None,
    missing_expires: bool = False,
) -> str:
    claims = {}
    if user_id is not None:
        claims["user_id"] = user_id
    if token_id is not None:
        claims["token_id"] = token_id
    if not missing_expires:
        claims["expires"] = expires
    return "sk-" + jwt.encode(claims=claims, key=secret_key, algorithm="HS256")


@pytest.fixture
def access_controller() -> AccessController:
    return AccessController()


@pytest.fixture
def admin_access_controller() -> AccessController:
    return AccessController(only_admin=True)


@pytest.fixture
def allow_expired_access_controller() -> AccessController:
    return AccessController(allow_expired=True)


@pytest.fixture
def secret_key() -> str:
    return "MY_SECRET_KEY"


@pytest.fixture
def key_encoder(secret_key) -> JwtKeyEncoder:
    return JwtKeyEncoder(secret_key=secret_key)


@pytest.fixture
def key_repository(db_session, key_encoder) -> PostgresKeyRepository:
    return PostgresKeyRepository(key_encoder=key_encoder, postgres_session=db_session)


@pytest.fixture
def authenticated_user_query(db_session) -> PostgresAuthenticatedUserQuery:
    return PostgresAuthenticatedUserQuery(postgres_session=db_session)


@pytest.fixture
def reset_request_context() -> ContextVar[RequestContext]:
    context_token: Token = request_context.set(RequestContext())
    yield request_context
    request_context.reset(context_token)


@pytest.fixture
def request_obj() -> Mock:
    return Mock()


@pytest.mark.asyncio(loop_scope="session")
class TestAccessController:
    async def test_should_raise_invalid_authentication_scheme_when_scheme_is_not_bearer(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
    ):
        # Arrange
        api_key = HTTPAuthorizationCredentials(scheme="Basic", credentials="sk-jwt-token")

        # Act / Assert
        with pytest.raises(InvalidAuthenticationSchemeHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_raise_invalid_api_key_when_credentials_are_empty(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
    ):
        # Arrange
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_raise_invalid_api_key_when_credentials_do_not_have_sk_prefix(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
    ):
        # Arrange
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials="jwt-token")

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_raise_invalid_api_key_when_jwt_decode_fails(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
    ):
        # Arrange
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials="sk-not-a-valid-jwt")

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_raise_invalid_api_key_when_user_id_claims_is_missing(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):

        credentials = _encode_api_key(secret_key=secret_key, user_id=None, token_id=1, expires=None)
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_raise_invalid_api_key_when_token_id_claims_is_missing(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        # Arrange
        credentials = _encode_api_key(secret_key=secret_key, user_id=1, token_id=None, expires=None)
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_raise_invalid_api_key_when_expires_claims_is_missing(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
    ):
        # Arrange
        credentials = _encode_api_key(secret_key=secret_key, user_id=1, token_id=1, expires=None, missing_expires=True)
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_raise_invalid_api_key_when_expires_claims_is_past(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
    ):
        # Arrange
        credentials = _encode_api_key(
            secret_key=secret_key,
            user_id=1,
            token_id=1,
            expires=int((datetime.now() - timedelta(days=1)).timestamp()),
        )
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_raise_invalid_api_key_when_key_not_found_in_repository(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()
        credentials = _encode_api_key(secret_key=secret_key, user_id=user.id, token_id=999999, expires=None)
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_raise_invalid_api_key_when_user_id_does_not_match_stored_user_id(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        # Arrange
        user = UserSQLFactory()
        user_2 = UserSQLFactory()
        token = KeySQLFactory(user=user, never_expires=True)
        await db_session.flush()

        credentials = _encode_api_key(
            secret_key=secret_key,
            user_id=user_2.id,
            token_id=token.id,
            expires=None,
        )
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    @pytest.mark.skipif(
        condition=datetime.now(tz=UTC) < datetime(2027, 8, 10, tzinfo=UTC),
        reason="Ignore test until 2027-08-10 due to legacy key expiration date unsync with database",
    )
    async def test_should_raise_invalid_api_key_when_expires_does_not_match_stored_expires(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        # Arrange
        user = UserSQLFactory()
        stored_expires = datetime.now() + timedelta(days=1)
        token = KeySQLFactory(user=user, expires=stored_expires)
        await db_session.flush()

        credentials = _encode_api_key(
            secret_key=secret_key,
            user_id=user.id,
            token_id=token.id,
            expires=int((datetime.now() + timedelta(days=2)).timestamp()),
        )
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        # Act / Assert
        with pytest.raises(InvalidAPIKeyHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_raise_account_expired_when_user_has_expired(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        # Arrange
        user = UserSQLFactory(expires=datetime.now() - timedelta(days=1))
        key = await create_key(db_session, secret_key=secret_key, user=user, never_expires=True)
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=key.token)

        # Act / Assert
        with pytest.raises(AccountExpiredHTTPException):
            await access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_allow_expired_user_when_allow_expired_is_true(
        self,
        allow_expired_access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        # Arrange
        user = UserSQLFactory(expires=datetime.now() - timedelta(days=1))
        key = await create_key(db_session, secret_key=secret_key, user=user, never_expires=True)
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=key.token)

        # Act
        await allow_expired_access_controller(
            request=request_obj,
            api_key=api_key,
            key_repository=key_repository,
            authenticated_user_query=authenticated_user_query,
            request_context=reset_request_context,
        )

        # Assert
        context = reset_request_context.get()
        assert context.user is not None
        assert context.user.id == user.id

    async def test_should_raise_not_admin_user_when_only_admin_is_required(
        self,
        admin_access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        # Arrange
        role = RoleSQLFactory()
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        user = UserSQLFactory(role=role)
        key = await create_key(db_session, secret_key=secret_key, user=user, never_expires=True)
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=key.token)

        # Act / Assert
        with pytest.raises(NotAdminUserHTTPException):
            await admin_access_controller(
                request=request_obj,
                api_key=api_key,
                key_repository=key_repository,
                authenticated_user_query=authenticated_user_query,
                request_context=reset_request_context,
            )

    async def test_should_set_key_and_user_in_request_context_when_access_is_valid(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        # Arrange
        user = UserSQLFactory()
        key = await create_key(db_session, secret_key=secret_key, user=user, never_expires=True)
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=key.token)

        # Act
        await access_controller(
            request=request_obj,
            api_key=api_key,
            key_repository=key_repository,
            authenticated_user_query=authenticated_user_query,
            request_context=reset_request_context,
        )

        # Assert
        context = reset_request_context.get()
        assert context.key is not None
        assert context.key.id == key.id
        assert context.key.user_id == user.id
        assert context.user is not None
        assert context.user.id == user.id
        assert context.user.email == user.email

    async def test_should_allow_admin_user_when_only_admin_is_required(
        self,
        admin_access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        # Arrange
        user = UserSQLFactory(admin_user=True)
        key = await create_key(db_session, secret_key=secret_key, user=user, never_expires=True)
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=key.token)

        # Act
        await admin_access_controller(
            request=request_obj,
            api_key=api_key,
            key_repository=key_repository,
            authenticated_user_query=authenticated_user_query,
            request_context=reset_request_context,
        )

        # Assert
        context = reset_request_context.get()
        assert context.key is not None
        assert context.key.id == key.id
        assert context.user is not None
        assert context.user.id == user.id
        assert context.user.is_admin is True

    async def test_should_validate_legacy_key_when_expires_is_in_expires_at(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        """
        Some legacy keys has expiration date unsync with database: after 2027-08-10, we can remove this test.
        """
        # Arrange
        user = UserSQLFactory()
        stored_expires = datetime.now(tz=UTC) + timedelta(days=1)
        token = KeySQLFactory(user=user, expires=stored_expires)
        await db_session.flush()

        credentials = "sk-" + jwt.encode(
            claims={"user_id": user.id, "token_id": token.id, "expires_at": int(stored_expires.timestamp())},
            key=secret_key,
            algorithm="HS256",
        )
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        # Act
        await access_controller(
            request=request_obj,
            api_key=api_key,
            key_repository=key_repository,
            authenticated_user_query=authenticated_user_query,
            request_context=reset_request_context,
        )

        # Assert
        context = reset_request_context.get()
        assert context.key is not None
        assert context.key.id == token.id
        assert context.key.user_id == user.id
        assert int(context.key.expires.timestamp()) == int(stored_expires.timestamp())

    async def test_should_validate_legacy_key_when_expiration_date_is_unsync_with_database(
        self,
        access_controller: AccessController,
        request_obj: Mock,
        key_repository: PostgresKeyRepository,
        authenticated_user_query: PostgresAuthenticatedUserQuery,
        reset_request_context: ContextVar[RequestContext],
        secret_key: str,
        db_session,
    ):
        """
        Some legacy keys has expiration date unsync with database: after 2027-08-10, we can remove this test.
        """
        # Arrange
        user = UserSQLFactory()
        database_stored_expires = datetime.now() + timedelta(days=1)
        token = KeySQLFactory(user=user, expires=database_stored_expires)
        await db_session.flush()

        key_stored_expires = int((datetime.now(tz=UTC) - timedelta(hours=1)).timestamp())
        credentials = "sk-" + jwt.encode(
            claims={"user_id": user.id, "token_id": token.id, "expires": key_stored_expires},
            key=secret_key,
            algorithm="HS256",
        )
        api_key = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        # Act
        await access_controller(
            request=request_obj,
            api_key=api_key,
            key_repository=key_repository,
            authenticated_user_query=authenticated_user_query,
            request_context=reset_request_context,
        )

        # Assert
        context = reset_request_context.get()
        assert context.key is not None
        assert context.key.id == token.id
        assert context.key.user_id == user.id
        assert int(context.key.expires.timestamp()) == key_stored_expires
