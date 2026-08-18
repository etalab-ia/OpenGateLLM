from unittest.mock import AsyncMock

from fastapi import Depends
import httpx
from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.dependencies import _key_encoder, auth_sso_login_use_case_factory, get_postgres_session
from api.domain.auth.errors import SSOAccessDeniedError, SsoInvalidSessionError, SsoProviderNotAvailableError
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import UserAlreadyExistsError, UserNotFoundError
from api.infrastructure.http import HttpAuthSsoSessionValidator
from api.infrastructure.postgres import PostgresKeyRepository, PostgresOrganizationRepository, PostgresRolesRepository, PostgresUserRepository
from api.tests.integration.factories.sql import OrganizationSQLFactory, RoleSQLFactory, UserSQLFactory
from api.use_cases.auth import AuthSsoLoginUseCase
from api.utils.variables import SYSTEM_PLAYGROUND_KEY_NAME, EndpointRoute

URL = f"/v1{EndpointRoute.AUTH_SSO_LOGIN}"

PLAYGROUND_URL = "http://playground:8501"
AUTH_URL = f"{PLAYGROUND_URL}/oauth2/auth"
SESSION_COOKIE = "_oauth2_proxy_opengatellm=valid-session"
ISSUER_URL = "https://issuer.example.com"
SUBJECT = "oidc-subject"
TOKEN_EXPIRES = 1893456000
EMAIL = "sso-user@test.com"


def _valid_body(**overrides) -> dict:
    body = {
        "sub": SUBJECT,
        "iss": ISSUER_URL,
        "exp": TOKEN_EXPIRES,
        "claims": {
            "name": "SSO User",
        },
    }
    body.update(overrides)
    return body


def _sso_login_headers(**overrides) -> dict:
    headers = {"Cookie": SESSION_COOKIE}
    headers.update(overrides)
    return headers


def _mock_valid_session(email: str = EMAIL) -> None:
    respx.get(url=AUTH_URL).mock(
        return_value=httpx.Response(
            status_code=202,
            headers={"X-Auth-Request-Email": email, "X-Auth-Request-User": email},
        )
    )


def _oidc_auth_sso_login_use_case_factory(default_role_id: int, default_organization_id: int):
    def factory(
        postgres_session=Depends(get_postgres_session),
        key_encoder=Depends(_key_encoder),
    ) -> AuthSsoLoginUseCase:
        return AuthSsoLoginUseCase(
            key_repository=PostgresKeyRepository(key_encoder=key_encoder, postgres_session=postgres_session),
            organization_repository=PostgresOrganizationRepository(postgres_session=postgres_session),
            user_repository=PostgresUserRepository(postgres_session=postgres_session),
            role_repository=PostgresRolesRepository(postgres_session=postgres_session),
            auth_sso_session_validator=HttpAuthSsoSessionValidator(auth_playground_url=PLAYGROUND_URL),
            auth_login_type="oidc",
            auth_sso_default_role_id=default_role_id,
            auth_sso_default_organization_id=default_organization_id,
        )

    return factory


@pytest.mark.asyncio(loop_scope="session")
class TestAuthSsoLogin:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session, app):
        role = RoleSQLFactory()
        organization = OrganizationSQLFactory()
        await db_session.flush()
        UserSQLFactory(email=EMAIL, role=role, organization=organization, sub=SUBJECT, iss=ISSUER_URL)
        await db_session.flush()
        app.dependency_overrides[auth_sso_login_use_case_factory] = _oidc_auth_sso_login_use_case_factory(
            default_role_id=role.id,
            default_organization_id=organization.id,
        )

    @respx.mock
    async def test_returns_401_when_cookie_header_is_missing(self, client: AsyncClient):
        response = await client.post(url=URL, json=_valid_body())

        assert response.status_code == 401
        assert response.json().get("detail") == "Invalid SSO session."

    @respx.mock
    async def test_happy_path(self, client: AsyncClient):
        _mock_valid_session()

        response = await client.post(url=URL, json=_valid_body(), headers=_sso_login_headers())

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "key"
        assert data["name"] == SYSTEM_PLAYGROUND_KEY_NAME
        assert isinstance(data["id"], int)
        assert data["value"].startswith("sk-")
        assert isinstance(data["expires"], int)
        assert isinstance(data["created"], int)

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                SsoInvalidSessionError(),
                401,
                "Invalid SSO session.",
            ),
            (
                SsoProviderNotAvailableError(),
                503,
                "SSO provider is not available.",
            ),
            (
                SSOAccessDeniedError(),
                403,
                "Access denied, please contact your administrator.",
            ),
            (
                RoleNotFoundError(id=99),
                404,
                "Role 99 not found.",
            ),
            (
                OrganizationNotFoundError(id=99),
                404,
                "Organization 99 not found.",
            ),
            (
                UserNotFoundError(email="missing@test.com"),
                404,
                "User missing@test.com not found.",
            ),
            (
                UserAlreadyExistsError(email="existing@test.com"),
                409,
                "User existing@test.com already exists.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[auth_sso_login_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            json=_valid_body(),
            headers=_sso_login_headers(),
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
