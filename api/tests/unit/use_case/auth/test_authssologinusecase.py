from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from api.domain.auth._authssosessionvalidator import SsoSessionClaims
from api.domain.auth.errors import InvalidOidcTokenError, SsoProviderNotAvailableError
from api.domain.key.entities import Key
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.auth import AuthSsoLoginCommand, AuthSsoLoginUseCase, AuthSsoLoginUseCaseSuccess

DEFAULT_ROLE_ID = 10
SESSION_COOKIE = "_oauth2_proxy_opengatellm=abc123"
AUTH_LOGIN_SESSION_DURATION = 3600
ISSUER_URL = "https://issuer.example.com"
SUBJECT = "oidc-subject"
TOKEN_EXPIRES = 1893456000


@pytest.fixture
def key_repository():
    return AsyncMock()


@pytest.fixture
def organization_repository():
    return AsyncMock()


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def auth_sso_session_validator():
    return AsyncMock()


@pytest.fixture
def use_case(
    key_repository,
    organization_repository,
    user_repository,
    auth_sso_session_validator,
):
    return AuthSsoLoginUseCase(
        key_repository=key_repository,
        organization_repository=organization_repository,
        user_repository=user_repository,
        auth_sso_session_validator=auth_sso_session_validator,
        auth_login_type="oidc",
        auth_sso_default_role_id=DEFAULT_ROLE_ID,
        auth_login_session_duration=AUTH_LOGIN_SESSION_DURATION,
    )


@pytest.fixture
def default_command():
    return AuthSsoLoginCommand(
        session_cookie=SESSION_COOKIE,
        name="Test User",
        organization=None,
        sub=SUBJECT,
        iss=ISSUER_URL,
        expires=TOKEN_EXPIRES,
    )


def _playground_key(user_id: int = 1) -> Key:
    return Key(
        id=42,
        name="playground",
        user_id=user_id,
        value="sk-test-token",
        expires=datetime(2030, 1, 1, tzinfo=UTC),
        created=datetime(2030, 1, 1, tzinfo=UTC),
    )


class TestAuthSsoLoginUseCase:
    @pytest.mark.asyncio
    async def test_should_return_invalid_oidc_token_error_when_login_type_is_password(
        self,
        key_repository,
        organization_repository,
        user_repository,
        auth_sso_session_validator,
        default_command,
    ):
        use_case = AuthSsoLoginUseCase(
            key_repository=key_repository,
            organization_repository=organization_repository,
            user_repository=user_repository,
            auth_sso_session_validator=auth_sso_session_validator,
            auth_login_type="password",
        )

        result = await use_case.execute(default_command)

        assert isinstance(result, InvalidOidcTokenError)
        auth_sso_session_validator.validate_session.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_refresh_playground_key_when_user_exists_and_session_is_valid(
        self,
        use_case,
        key_repository,
        user_repository,
        auth_sso_session_validator,
        default_command,
    ):
        user = UserFactory(id=1, email="user@test.com")
        auth_sso_session_validator.validate_session.return_value = SsoSessionClaims(email="user@test.com")
        user_repository.get_user_by_email.return_value = user
        refreshed_key = _playground_key(user_id=1)
        key_repository.upsert_key.return_value = refreshed_key

        result = await use_case.execute(default_command)

        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        assert result.key.id == 42
        auth_sso_session_validator.validate_session.assert_awaited_once_with(session_cookie=SESSION_COOKIE)
        user_repository.get_user_by_email.assert_awaited_once_with(email="user@test.com")
        key_repository.upsert_key.assert_awaited_once()
        expire = key_repository.upsert_key.await_args.kwargs["expire"]
        assert expire == datetime.fromtimestamp(TOKEN_EXPIRES, tz=UTC)

    @pytest.mark.asyncio
    async def test_should_use_session_duration_when_expires_is_not_provided(
        self,
        use_case,
        key_repository,
        user_repository,
        auth_sso_session_validator,
    ):
        command = AuthSsoLoginCommand(
            session_cookie=SESSION_COOKIE,
            name="Test User",
            organization=None,
        )
        user = UserFactory(id=1, email="user@test.com")
        auth_sso_session_validator.validate_session.return_value = SsoSessionClaims(email="user@test.com")
        user_repository.get_user_by_email.return_value = user
        key_repository.upsert_key.return_value = _playground_key()

        result = await use_case.execute(command)

        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        expire = key_repository.upsert_key.await_args.kwargs["expire"]
        assert expire.tzinfo == UTC
        assert expire > datetime.now(tz=UTC)
        assert expire <= datetime.now(tz=UTC) + timedelta(seconds=AUTH_LOGIN_SESSION_DURATION + 1)

    @pytest.mark.asyncio
    async def test_should_return_sso_provider_not_available_error_when_session_validation_fails(
        self,
        use_case,
        auth_sso_session_validator,
        default_command,
    ):
        error = SsoProviderNotAvailableError(message="Playground unavailable")
        auth_sso_session_validator.validate_session.return_value = error

        result = await use_case.execute(default_command)

        assert isinstance(result, SsoProviderNotAvailableError)
        assert result.message == "Playground unavailable"

    @pytest.mark.asyncio
    async def test_should_return_invalid_oidc_token_error_when_session_is_invalid(
        self,
        use_case,
        auth_sso_session_validator,
        default_command,
    ):
        error = InvalidOidcTokenError(message="Invalid or expired oauth2-proxy session")
        auth_sso_session_validator.validate_session.return_value = error

        result = await use_case.execute(default_command)

        assert isinstance(result, InvalidOidcTokenError)
        assert result.message == "Invalid or expired oauth2-proxy session"

    @pytest.mark.asyncio
    async def test_should_create_user_when_user_does_not_exist(
        self,
        use_case,
        key_repository,
        user_repository,
        auth_sso_session_validator,
        default_command,
    ):
        created_user = UserFactory(id=7, email="user@test.com", name="Test User")
        auth_sso_session_validator.validate_session.return_value = SsoSessionClaims(email="user@test.com")
        user_repository.get_user_by_email.return_value = UserNotFoundError(email="user@test.com")
        user_repository.create_user.return_value = created_user
        key_repository.upsert_key.return_value = _playground_key(user_id=7)

        result = await use_case.execute(default_command)

        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        user_repository.create_user.assert_awaited_once_with(
            role_id=DEFAULT_ROLE_ID,
            email="user@test.com",
            name="Test User",
            organization_id=None,
            sub=SUBJECT,
            iss=ISSUER_URL,
        )

    @pytest.mark.asyncio
    async def test_should_create_user_with_existing_organization(
        self,
        use_case,
        key_repository,
        organization_repository,
        user_repository,
        auth_sso_session_validator,
    ):
        command = AuthSsoLoginCommand(
            session_cookie=SESSION_COOKIE,
            name="Test User",
            organization="Acme Corp",
            sub=SUBJECT,
            iss=ISSUER_URL,
        )
        organization = Organization(
            id=5,
            name="Acme Corp",
            users=0,
            created=datetime(2024, 1, 1, tzinfo=UTC),
            updated=datetime(2024, 1, 1, tzinfo=UTC),
        )
        created_user = UserFactory(id=7, email="user@test.com", organization_id=5)
        auth_sso_session_validator.validate_session.return_value = SsoSessionClaims(email="user@test.com")
        user_repository.get_user_by_email.return_value = UserNotFoundError(email="user@test.com")
        organization_repository.get_organization_by_name.return_value = organization
        user_repository.create_user.return_value = created_user
        key_repository.upsert_key.return_value = _playground_key(user_id=7)

        result = await use_case.execute(command)

        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        organization_repository.get_organization_by_name.assert_awaited_once_with(name="Acme Corp")
        organization_repository.create_organization.assert_not_awaited()
        user_repository.create_user.assert_awaited_once_with(
            role_id=DEFAULT_ROLE_ID,
            email="user@test.com",
            name="Test User",
            organization_id=5,
            sub=SUBJECT,
            iss=ISSUER_URL,
        )

    @pytest.mark.asyncio
    async def test_should_create_organization_and_user_when_organization_does_not_exist(
        self,
        use_case,
        key_repository,
        organization_repository,
        user_repository,
        auth_sso_session_validator,
    ):
        command = AuthSsoLoginCommand(
            session_cookie=SESSION_COOKIE,
            name="Test User",
            organization="New Org",
            sub=SUBJECT,
            iss=ISSUER_URL,
        )
        created_organization = Organization(
            id=9,
            name="New Org",
            users=0,
            created=datetime(2024, 1, 1, tzinfo=UTC),
            updated=datetime(2024, 1, 1, tzinfo=UTC),
        )
        created_user = UserFactory(id=7, email="user@test.com", organization_id=9)
        auth_sso_session_validator.validate_session.return_value = SsoSessionClaims(email="user@test.com")
        user_repository.get_user_by_email.return_value = UserNotFoundError(email="user@test.com")
        organization_repository.get_organization_by_name.return_value = OrganizationNotFoundError(name="New Org")
        organization_repository.create_organization.return_value = created_organization
        user_repository.create_user.return_value = created_user
        key_repository.upsert_key.return_value = _playground_key(user_id=7)

        result = await use_case.execute(command)

        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        organization_repository.create_organization.assert_awaited_once_with(name="New Org")
        user_repository.create_user.assert_awaited_once_with(
            role_id=DEFAULT_ROLE_ID,
            email="user@test.com",
            name="Test User",
            organization_id=9,
            sub=SUBJECT,
            iss=ISSUER_URL,
        )

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_default_role_does_not_exist(
        self,
        use_case,
        user_repository,
        auth_sso_session_validator,
        default_command,
    ):
        error = RoleNotFoundError(id=DEFAULT_ROLE_ID)
        auth_sso_session_validator.validate_session.return_value = SsoSessionClaims(email="user@test.com")
        user_repository.get_user_by_email.return_value = UserNotFoundError(email="user@test.com")
        user_repository.create_user.return_value = error

        result = await use_case.execute(default_command)

        assert isinstance(result, RoleNotFoundError)
        assert result.id == DEFAULT_ROLE_ID
