from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from fastapi import Depends
import httpx
from httpx import AsyncClient
from jose import jwk, jwt
import pytest
import pytest_asyncio
import respx
import rsa

from api.dependencies import _auth_sso_provider_cache, _key_encoder, auth_sso_login_use_case_factory, get_postgres_session
from api.domain.auth.errors import InvalidOidcTokenError, SsoProviderNotAvailableError
from api.domain.role.errors import RoleNotFoundError
from api.infrastructure.http import HttpAuthSsoProviderClient
from api.infrastructure.jwt import JwtAuthSsoTokenValidator
from api.infrastructure.postgres import PostgresKeyRepository, PostgresOrganizationRepository, PostgresUserRepository
from api.tests.integration.factories.sql import RoleSQLFactory, UserSQLFactory
from api.use_cases.auth import AuthSsoLoginUseCase
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.AUTH_SSO_LOGIN}"

ISSUER_URL = "http://my-test-issuer/"
JWKS_URI = "http://my-test-issuer/jwks"
CLIENT_ID = "test-client-id"
AUTH_LOGIN_SESSION_DURATION = 3600

_oidc_settings = {"default_role_id": 1}


@dataclass(frozen=True)
class RsaTestKey:
    signing_key: object
    public_jwk: dict


@pytest.fixture(scope="module")
def rsa_test_key() -> RsaTestKey:
    _, private_key = rsa.newkeys(2048)
    signing_key = jwk.construct(private_key.save_pkcs1().decode(), algorithm="RS256")
    public_jwk = signing_key.public_key().to_dict()
    public_jwk.update({"kid": "rsa-test-kid", "use": "sig", "alg": "RS256"})
    return RsaTestKey(signing_key=signing_key, public_jwk=public_jwk)


def _discovery_url(issuer_url: str) -> str:
    return f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"


def _encode_token(rsa_test_key: RsaTestKey, *, client_id: str = CLIENT_ID) -> str:
    expires_at = datetime.now(tz=UTC) + timedelta(hours=1)
    return jwt.encode(
        claims={
            "sub": "oidc-subject",
            "aud": client_id,
            "iss": ISSUER_URL,
            "exp": int(expires_at.timestamp()),
        },
        key=rsa_test_key.signing_key,
        algorithm="RS256",
        headers={"kid": "rsa-test-kid"},
    )


def _valid_body(rsa_test_key: RsaTestKey, **overrides) -> dict:
    body = {
        "email": "sso-user@test.com",
        "name": "SSO User",
        "token": _encode_token(rsa_test_key),
    }
    body.update(overrides)
    return body


def _mock_oidc_jwks(rsa_test_key: RsaTestKey) -> None:
    respx.get(url=_discovery_url(ISSUER_URL)).mock(return_value=httpx.Response(status_code=200, json={"jwks_uri": JWKS_URI}))
    respx.get(url=JWKS_URI).mock(return_value=httpx.Response(status_code=200, json={"keys": [rsa_test_key.public_jwk]}))


def oidc_auth_sso_login_use_case_factory(
    postgres_session=Depends(get_postgres_session),
    key_encoder=Depends(_key_encoder),
    auth_sso_provider_cache=Depends(_auth_sso_provider_cache),
) -> AuthSsoLoginUseCase:
    return AuthSsoLoginUseCase(
        key_repository=PostgresKeyRepository(key_encoder=key_encoder, postgres_session=postgres_session),
        organization_repository=PostgresOrganizationRepository(postgres_session=postgres_session),
        user_repository=PostgresUserRepository(postgres_session=postgres_session),
        auth_sso_provider_client=HttpAuthSsoProviderClient(issuer_url=ISSUER_URL),
        auth_sso_token_validator=JwtAuthSsoTokenValidator(),
        auth_sso_provider_cache=auth_sso_provider_cache,
        auth_login_type="oidc",
        auth_sso_oidc_issuer_url=ISSUER_URL,
        auth_sso_client_id=CLIENT_ID,
        auth_sso_default_role_id=_oidc_settings["default_role_id"],
        auth_login_session_duration=AUTH_LOGIN_SESSION_DURATION,
    )


@pytest.mark.asyncio(loop_scope="session")
class TestAuthSsoLogin:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session, app):
        role = RoleSQLFactory()
        await db_session.flush()
        _oidc_settings["default_role_id"] = role.id
        UserSQLFactory(email="sso-user@test.com", role=role)
        await db_session.flush()
        app.dependency_overrides[auth_sso_login_use_case_factory] = oidc_auth_sso_login_use_case_factory

    @respx.mock
    async def test_happy_path(self, client: AsyncClient, rsa_test_key: RsaTestKey):
        _mock_oidc_jwks(rsa_test_key)

        response = await client.post(url=URL, json=_valid_body(rsa_test_key))

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "key"
        assert data["name"] == "playground"
        assert isinstance(data["id"], int)
        assert data["value"].startswith("sk-")
        assert isinstance(data["expires"], int)
        assert isinstance(data["created"], int)

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                InvalidOidcTokenError(),
                401,
                "Invalid OIDC token.",
            ),
            (
                SsoProviderNotAvailableError(),
                503,
                "OIDC provider is not available.",
            ),
            (
                RoleNotFoundError(id=99),
                404,
                "Role 99 not found.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[auth_sso_login_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            json={
                "email": "sso-user@test.com",
                "token": "oidc-token",
            },
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
