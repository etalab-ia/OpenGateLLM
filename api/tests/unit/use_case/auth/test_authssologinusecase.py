from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from api.domain.auth.errors import SSOAccessDeniedError, SsoInvalidSessionError, SsoProviderNotAvailableError
from api.domain.key.entities import Key
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.auth import AuthSsoLoginCommand, AuthSsoLoginUseCase, AuthSsoLoginUseCaseSuccess

DEFAULT_ROLE_ID = 10
DEFAULT_ORGANIZATION_ID = 1
SESSION_COOKIE = "_oauth2_proxy_opengatellm=abc123"
ISSUER_URL = "https://issuer.example.com"
SUBJECT = "oidc-subject"
TOKEN_EXPIRES = 1893456000
EMAIL = "user@test.com"


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
def role_repository():
    return AsyncMock()


@pytest.fixture
def auth_sso_session_validator():
    return AsyncMock()


@pytest.fixture
def use_case(
    key_repository,
    organization_repository,
    user_repository,
    role_repository,
    auth_sso_session_validator,
):
    return AuthSsoLoginUseCase(
        key_repository=key_repository,
        organization_repository=organization_repository,
        user_repository=user_repository,
        role_repository=role_repository,
        auth_sso_session_validator=auth_sso_session_validator,
        auth_login_type="oidc",
        auth_sso_default_role_id=DEFAULT_ROLE_ID,
        auth_sso_default_organization_id=DEFAULT_ORGANIZATION_ID,
    )


@pytest.fixture
def default_command():
    return AuthSsoLoginCommand(
        session_cookie=SESSION_COOKIE,
        sub=SUBJECT,
        iss=ISSUER_URL,
        exp=TOKEN_EXPIRES,
        claims={"name": "Test User"},
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
    async def test_should_return_invalid_session_error_when_login_type_is_password(
        self,
        key_repository,
        organization_repository,
        user_repository,
        role_repository,
        auth_sso_session_validator,
        default_command,
    ):
        use_case = AuthSsoLoginUseCase(
            key_repository=key_repository,
            organization_repository=organization_repository,
            user_repository=user_repository,
            role_repository=role_repository,
            auth_sso_session_validator=auth_sso_session_validator,
            auth_login_type="password",
            auth_sso_default_role_id=DEFAULT_ROLE_ID,
            auth_sso_default_organization_id=DEFAULT_ORGANIZATION_ID,
        )

        result = await use_case.execute(default_command)

        assert isinstance(result, SsoInvalidSessionError)
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
        user = UserFactory(
            id=1,
            email=EMAIL,
            name=None,
            sub=SUBJECT,
            iss=ISSUER_URL,
            role=DEFAULT_ROLE_ID,
            organization_id=DEFAULT_ORGANIZATION_ID,
            claims={"name": "Test User"},
        )
        auth_sso_session_validator.validate_session.return_value = EMAIL
        user_repository.get_user_by_iss_and_sub.return_value = user
        refreshed_key = _playground_key(user_id=1)
        key_repository.upsert_key.return_value = refreshed_key

        result = await use_case.execute(default_command)

        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        assert result.key.id == 42
        auth_sso_session_validator.validate_session.assert_awaited_once_with(session_cookie=SESSION_COOKIE)
        user_repository.get_user_by_iss_and_sub.assert_awaited_once_with(iss=ISSUER_URL, sub=SUBJECT)
        user_repository.update_user.assert_not_awaited()
        key_repository.upsert_key.assert_awaited_once()
        expire = key_repository.upsert_key.await_args.kwargs["expire"]
        assert expire == datetime.fromtimestamp(TOKEN_EXPIRES, tz=UTC)

    @pytest.mark.asyncio
    async def test_should_update_role_organization_and_claims_when_they_change(
        self,
        use_case,
        key_repository,
        user_repository,
        auth_sso_session_validator,
        default_command,
    ):
        user = UserFactory(
            id=1,
            email=EMAIL,
            name=None,
            sub=SUBJECT,
            iss=ISSUER_URL,
            role=DEFAULT_ROLE_ID,
            organization_id=DEFAULT_ORGANIZATION_ID,
            claims={"old": True},
        )
        updated_user = user.model_copy(update={"role": 20, "organization_id": 5, "claims": default_command.claims, "name": "Custom Name"})
        auth_sso_session_validator.validate_session.return_value = EMAIL
        user_repository.get_user_by_iss_and_sub.return_value = user
        user_repository.update_user.return_value = updated_user
        key_repository.upsert_key.return_value = _playground_key()

        use_case.get_role_id = AsyncMock(return_value=20)
        use_case.get_organization_id = AsyncMock(return_value=5)
        use_case.get_user_name = AsyncMock(return_value="Custom Name")

        result = await use_case.execute(default_command)

        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        user_repository.update_user.assert_awaited_once()
        updated = user_repository.update_user.await_args.kwargs["user"]
        assert updated.email == EMAIL
        assert updated.role == 20
        assert updated.organization_id == 5
        assert updated.name == "Custom Name"
        assert updated.claims == default_command.claims

    @pytest.mark.asyncio
    async def test_should_update_email_when_session_email_changed_for_existing_user(
        self,
        use_case,
        user_repository,
        key_repository,
        auth_sso_session_validator,
        default_command,
    ):
        new_email = "new@test.com"
        user = UserFactory(
            id=1,
            email=EMAIL,
            name=None,
            sub=SUBJECT,
            iss=ISSUER_URL,
            role=DEFAULT_ROLE_ID,
            organization_id=DEFAULT_ORGANIZATION_ID,
            claims={"name": "Test User"},
        )
        updated_user = user.model_copy(update={"email": new_email})
        auth_sso_session_validator.validate_session.return_value = new_email
        user_repository.get_user_by_iss_and_sub.return_value = user
        user_repository.update_user.return_value = updated_user
        key_repository.upsert_key.return_value = _playground_key()

        result = await use_case.execute(default_command)

        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        user_repository.update_user.assert_awaited_once()
        assert user_repository.update_user.await_args.kwargs["user"].email == new_email

    @pytest.mark.asyncio
    async def test_should_link_existing_user_found_by_email_and_override_iss_sub(
        self,
        use_case,
        user_repository,
        key_repository,
        auth_sso_session_validator,
        default_command,
    ):
        existing_user = UserFactory(
            id=2,
            email=EMAIL,
            name=None,
            sub="other-sub",
            iss="https://other-issuer.example.com",
            role=DEFAULT_ROLE_ID,
            organization_id=DEFAULT_ORGANIZATION_ID,
            claims=None,
        )
        updated_user = existing_user.model_copy(
            update={
                "sub": SUBJECT,
                "iss": ISSUER_URL,
                "claims": default_command.claims,
            }
        )
        auth_sso_session_validator.validate_session.return_value = EMAIL
        user_repository.get_user_by_iss_and_sub.return_value = UserNotFoundError()
        user_repository.get_user_by_email.return_value = existing_user
        user_repository.update_user.return_value = updated_user
        key_repository.upsert_key.return_value = _playground_key(user_id=2)

        result = await use_case.execute(default_command)

        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        user_repository.create_user.assert_not_awaited()
        user_repository.update_user.assert_awaited_once()
        updated = user_repository.update_user.await_args.kwargs["user"]
        assert updated.id == 2
        assert updated.sub == SUBJECT
        assert updated.iss == ISSUER_URL
        assert updated.claims == default_command.claims
        key_repository.upsert_key.assert_awaited_once()

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
    async def test_should_return_invalid_session_error_when_session_is_invalid(
        self,
        use_case,
        auth_sso_session_validator,
        default_command,
    ):
        error = SsoInvalidSessionError(message="Invalid or expired oauth2-proxy session")
        auth_sso_session_validator.validate_session.return_value = error

        result = await use_case.execute(default_command)

        assert isinstance(result, SsoInvalidSessionError)
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
        created_user = UserFactory(
            id=7,
            email=EMAIL,
            name=None,
            sub=SUBJECT,
            iss=ISSUER_URL,
            role=DEFAULT_ROLE_ID,
            organization_id=DEFAULT_ORGANIZATION_ID,
            claims={"name": "Test User"},
        )
        auth_sso_session_validator.validate_session.return_value = EMAIL
        user_repository.get_user_by_iss_and_sub.return_value = UserNotFoundError()
        user_repository.get_user_by_email.return_value = UserNotFoundError(email=EMAIL)
        user_repository.create_user.return_value = created_user
        key_repository.upsert_key.return_value = _playground_key(user_id=7)

        result = await use_case.execute(default_command)

        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        user_repository.create_user.assert_awaited_once_with(
            role_id=DEFAULT_ROLE_ID,
            email=EMAIL,
            name=None,
            organization_id=DEFAULT_ORGANIZATION_ID,
            sub=SUBJECT,
            iss=ISSUER_URL,
            claims={"name": "Test User"},
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
        auth_sso_session_validator.validate_session.return_value = EMAIL
        user_repository.get_user_by_iss_and_sub.return_value = UserNotFoundError()
        user_repository.get_user_by_email.return_value = UserNotFoundError(email=EMAIL)
        user_repository.create_user.return_value = error

        result = await use_case.execute(default_command)

        assert isinstance(result, RoleNotFoundError)
        assert result.id == DEFAULT_ROLE_ID

    @pytest.mark.asyncio
    async def test_should_deny_access_when_has_access_returns_false(
        self,
        use_case,
        user_repository,
        auth_sso_session_validator,
        default_command,
    ):
        auth_sso_session_validator.validate_session.return_value = EMAIL
        use_case.has_access = AsyncMock(return_value=False)

        result = await use_case.execute(default_command)

        assert isinstance(result, SSOAccessDeniedError)
        user_repository.get_user_by_iss_and_sub.assert_not_awaited()
