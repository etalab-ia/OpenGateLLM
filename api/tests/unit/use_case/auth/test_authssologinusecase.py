from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from api.domain.auth.errors import InvalidOidcTokenError, SsoProviderNotAvailableError
from api.domain.key.entities import Key
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.auth import AuthSsoLoginCommand, AuthSsoLoginUseCase, AuthSsoLoginUseCaseSuccess

ISSUER_URL = "https://issuer.example.com"
CLIENT_ID = "client-id"
DEFAULT_ROLE_ID = 10
JWKS = {"keys": [{"kid": "test-kid"}]}
CLAIMS = {
    "sub": "oidc-subject",
    "iss": ISSUER_URL,
    "exp": 1893456000,
}


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
def auth_sso_provider_client():
    return AsyncMock()


@pytest.fixture
def auth_sso_token_validator():
    return AsyncMock()


@pytest.fixture
def auth_sso_provider_cache():
    return AsyncMock()


@pytest.fixture
def use_case(
    key_repository,
    organization_repository,
    user_repository,
    auth_sso_provider_client,
    auth_sso_token_validator,
    auth_sso_provider_cache,
):
    return AuthSsoLoginUseCase(
        key_repository=key_repository,
        organization_repository=organization_repository,
        user_repository=user_repository,
        auth_sso_provider_client=auth_sso_provider_client,
        auth_sso_token_validator=auth_sso_token_validator,
        auth_sso_provider_cache=auth_sso_provider_cache,
        auth_login_type="oidc",
        auth_sso_oidc_issuer_url=ISSUER_URL,
        auth_sso_client_id=CLIENT_ID,
        auth_sso_default_role_id=DEFAULT_ROLE_ID,
        auth_login_session_duration=3600,
    )


@pytest.fixture
def default_command():
    return AuthSsoLoginCommand(
        email="user@test.com",
        name="Test User",
        organization=None,
        token="oidc-token",
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
        auth_sso_provider_client,
        auth_sso_token_validator,
        auth_sso_provider_cache,
        default_command,
    ):
        # Arrange
        use_case = AuthSsoLoginUseCase(
            key_repository=key_repository,
            organization_repository=organization_repository,
            user_repository=user_repository,
            auth_sso_provider_client=auth_sso_provider_client,
            auth_sso_token_validator=auth_sso_token_validator,
            auth_sso_provider_cache=auth_sso_provider_cache,
            auth_login_type="password",
        )

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, InvalidOidcTokenError)
        auth_sso_provider_cache.get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_refresh_playground_key_when_user_exists_and_token_is_valid(
        self,
        use_case,
        key_repository,
        user_repository,
        auth_sso_provider_cache,
        auth_sso_token_validator,
        default_command,
    ):
        # Arrange
        user = UserFactory(id=1, email="user@test.com")
        auth_sso_provider_cache.get.return_value = JWKS
        auth_sso_token_validator.validate_token.return_value = CLAIMS
        user_repository.get_user_by_email.return_value = user
        refreshed_key = _playground_key(user_id=1)
        key_repository.upsert_key.return_value = refreshed_key

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        assert result.key.id == 42
        assert result.key.name == "playground"
        auth_sso_provider_cache.get.assert_awaited_once_with(email=ISSUER_URL)
        auth_sso_token_validator.validate_token.assert_awaited_once_with(
            token="oidc-token",
            client_id=CLIENT_ID,
            jwks=JWKS,
        )
        user_repository.get_user_by_email.assert_awaited_once_with(email="user@test.com")
        key_repository.upsert_key.assert_awaited_once()
        assert key_repository.upsert_key.await_args.kwargs["user_id"] == 1
        assert key_repository.upsert_key.await_args.kwargs["name"] == "playground"
        assert key_repository.upsert_key.await_args.kwargs["expire"] == datetime.fromtimestamp(CLAIMS["exp"], tz=UTC)

    @pytest.mark.asyncio
    async def test_should_fetch_jwks_when_cache_is_empty(
        self,
        use_case,
        key_repository,
        user_repository,
        auth_sso_provider_cache,
        auth_sso_provider_client,
        auth_sso_token_validator,
        default_command,
    ):
        # Arrange
        user = UserFactory(id=1, email="user@test.com")
        auth_sso_provider_cache.get.return_value = None
        auth_sso_provider_client.get_jwks.return_value = JWKS
        auth_sso_token_validator.validate_token.return_value = CLAIMS
        user_repository.get_user_by_email.return_value = user
        key_repository.upsert_key.return_value = _playground_key()

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        auth_sso_provider_client.get_jwks.assert_awaited_once_with(issuer_url=ISSUER_URL)
        auth_sso_provider_cache.set.assert_awaited_once_with(
            email=ISSUER_URL,
            claims=JWKS,
            expire=3600,
        )

    @pytest.mark.asyncio
    async def test_should_return_sso_provider_not_available_error_when_jwks_fetch_fails(
        self,
        use_case,
        auth_sso_provider_cache,
        auth_sso_provider_client,
        default_command,
    ):
        # Arrange
        error = SsoProviderNotAvailableError(message="OIDC server unavailable")
        auth_sso_provider_cache.get.return_value = None
        auth_sso_provider_client.get_jwks.return_value = error

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, SsoProviderNotAvailableError)
        assert result.message == "OIDC server unavailable"

    @pytest.mark.asyncio
    async def test_should_return_invalid_oidc_token_error_when_token_validation_fails(
        self,
        use_case,
        auth_sso_provider_cache,
        auth_sso_token_validator,
        default_command,
    ):
        # Arrange
        error = InvalidOidcTokenError(message="JWT validation failed")
        auth_sso_provider_cache.get.return_value = JWKS
        auth_sso_token_validator.validate_token.return_value = error

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, InvalidOidcTokenError)
        assert result.message == "JWT validation failed"

    @pytest.mark.asyncio
    async def test_should_retry_validation_with_fresh_jwks_when_jwks_are_stale(
        self,
        use_case,
        key_repository,
        user_repository,
        auth_sso_provider_cache,
        auth_sso_provider_client,
        auth_sso_token_validator,
        default_command,
    ):
        # Arrange
        refreshed_jwks = {"keys": [{"kid": "new-kid"}]}
        user = UserFactory(id=1, email="user@test.com")
        auth_sso_provider_cache.get.return_value = JWKS
        auth_sso_token_validator.validate_token.side_effect = [
            InvalidOidcTokenError(message="No matching key found for kid", stale_jwks=True),
            CLAIMS,
        ]
        auth_sso_provider_client.get_jwks.return_value = refreshed_jwks
        user_repository.get_user_by_email.return_value = user
        key_repository.upsert_key.return_value = _playground_key()

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        auth_sso_provider_cache.delete.assert_awaited_once_with(email=ISSUER_URL)
        auth_sso_provider_client.get_jwks.assert_awaited_once_with(issuer_url=ISSUER_URL)
        auth_sso_provider_cache.set.assert_awaited_once_with(
            email=ISSUER_URL,
            claims=refreshed_jwks,
            expire=3600,
        )
        assert auth_sso_token_validator.validate_token.await_count == 2
        assert auth_sso_token_validator.validate_token.await_args_list[1].kwargs["jwks"] == refreshed_jwks

    @pytest.mark.asyncio
    async def test_should_return_sso_provider_not_available_error_when_jwks_refresh_fails_after_stale_validation(
        self,
        use_case,
        auth_sso_provider_cache,
        auth_sso_provider_client,
        auth_sso_token_validator,
        default_command,
    ):
        # Arrange
        error = SsoProviderNotAvailableError(message="Error fetching JWKS")
        auth_sso_provider_cache.get.return_value = JWKS
        auth_sso_token_validator.validate_token.return_value = InvalidOidcTokenError(stale_jwks=True)
        auth_sso_provider_client.get_jwks.return_value = error

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, SsoProviderNotAvailableError)
        assert result.message == "Error fetching JWKS"

    @pytest.mark.asyncio
    async def test_should_create_user_when_user_does_not_exist(
        self,
        use_case,
        key_repository,
        user_repository,
        auth_sso_provider_cache,
        auth_sso_token_validator,
        default_command,
    ):
        # Arrange
        created_user = UserFactory(id=7, email="user@test.com", name="Test User", sub="oidc-subject", iss=ISSUER_URL)
        auth_sso_provider_cache.get.return_value = JWKS
        auth_sso_token_validator.validate_token.return_value = CLAIMS
        user_repository.get_user_by_email.return_value = UserNotFoundError(email="user@test.com")
        user_repository.create_user.return_value = created_user
        key_repository.upsert_key.return_value = _playground_key(user_id=7)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        user_repository.create_user.assert_awaited_once_with(
            role_id=DEFAULT_ROLE_ID,
            email="user@test.com",
            name="Test User",
            organization_id=None,
            sub="oidc-subject",
            iss=ISSUER_URL,
        )

    @pytest.mark.asyncio
    async def test_should_create_user_with_existing_organization(
        self,
        use_case,
        key_repository,
        organization_repository,
        user_repository,
        auth_sso_provider_cache,
        auth_sso_token_validator,
    ):
        # Arrange
        command = AuthSsoLoginCommand(
            email="user@test.com",
            name="Test User",
            organization="Acme Corp",
            token="oidc-token",
        )
        organization = Organization(
            id=5,
            name="Acme Corp",
            users=0,
            created=datetime(2024, 1, 1, tzinfo=UTC),
            updated=datetime(2024, 1, 1, tzinfo=UTC),
        )
        created_user = UserFactory(id=7, email="user@test.com", organization_id=5)
        auth_sso_provider_cache.get.return_value = JWKS
        auth_sso_token_validator.validate_token.return_value = CLAIMS
        user_repository.get_user_by_email.return_value = UserNotFoundError(email="user@test.com")
        organization_repository.get_organization_by_name.return_value = organization
        user_repository.create_user.return_value = created_user
        key_repository.upsert_key.return_value = _playground_key(user_id=7)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        organization_repository.get_organization_by_name.assert_awaited_once_with(name="Acme Corp")
        organization_repository.create_organization.assert_not_awaited()
        user_repository.create_user.assert_awaited_once_with(
            role_id=DEFAULT_ROLE_ID,
            email="user@test.com",
            name="Test User",
            organization_id=5,
            sub="oidc-subject",
            iss=ISSUER_URL,
        )

    @pytest.mark.asyncio
    async def test_should_create_organization_and_user_when_organization_does_not_exist(
        self,
        use_case,
        key_repository,
        organization_repository,
        user_repository,
        auth_sso_provider_cache,
        auth_sso_token_validator,
    ):
        # Arrange
        command = AuthSsoLoginCommand(
            email="user@test.com",
            name="Test User",
            organization="New Org",
            token="oidc-token",
        )
        created_organization = Organization(
            id=9,
            name="New Org",
            users=0,
            created=datetime(2024, 1, 1, tzinfo=UTC),
            updated=datetime(2024, 1, 1, tzinfo=UTC),
        )
        created_user = UserFactory(id=7, email="user@test.com", organization_id=9)
        auth_sso_provider_cache.get.return_value = JWKS
        auth_sso_token_validator.validate_token.return_value = CLAIMS
        user_repository.get_user_by_email.return_value = UserNotFoundError(email="user@test.com")
        organization_repository.get_organization_by_name.return_value = OrganizationNotFoundError(name="New Org")
        organization_repository.create_organization.return_value = created_organization
        user_repository.create_user.return_value = created_user
        key_repository.upsert_key.return_value = _playground_key(user_id=7)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        organization_repository.create_organization.assert_awaited_once_with(name="New Org")
        user_repository.create_user.assert_awaited_once_with(
            role_id=DEFAULT_ROLE_ID,
            email="user@test.com",
            name="Test User",
            organization_id=9,
            sub="oidc-subject",
            iss=ISSUER_URL,
        )

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_default_role_does_not_exist(
        self,
        use_case,
        user_repository,
        auth_sso_provider_cache,
        auth_sso_token_validator,
        default_command,
    ):
        # Arrange
        error = RoleNotFoundError(id=DEFAULT_ROLE_ID)
        auth_sso_provider_cache.get.return_value = JWKS
        auth_sso_token_validator.validate_token.return_value = CLAIMS
        user_repository.get_user_by_email.return_value = UserNotFoundError(email="user@test.com")
        user_repository.create_user.return_value = error

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == DEFAULT_ROLE_ID

    @pytest.mark.asyncio
    async def test_should_use_session_duration_when_claims_do_not_contain_exp(
        self,
        use_case,
        key_repository,
        user_repository,
        auth_sso_provider_cache,
        auth_sso_token_validator,
        default_command,
    ):
        # Arrange
        user = UserFactory(id=1, email="user@test.com")
        claims_without_exp = {"sub": "oidc-subject", "iss": ISSUER_URL}
        auth_sso_provider_cache.get.return_value = JWKS
        auth_sso_token_validator.validate_token.return_value = claims_without_exp
        user_repository.get_user_by_email.return_value = user
        key_repository.upsert_key.return_value = _playground_key()

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, AuthSsoLoginUseCaseSuccess)
        expire = key_repository.upsert_key.await_args.kwargs["expire"]
        assert expire.tzinfo == UTC
        assert expire > datetime.now(tz=UTC)
