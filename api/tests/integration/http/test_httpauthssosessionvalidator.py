import httpx
import pytest
import respx

from api.domain.auth.errors import InvalidOidcTokenError, SsoProviderNotAvailableError
from api.infrastructure.http import HttpAuthSsoSessionValidator

PLAYGROUND_URL = "http://playground:8501"
AUTH_URL = f"{PLAYGROUND_URL}/oauth2/auth"
SESSION_COOKIE = "_oauth2_proxy_opengatellm=valid-session"


@pytest.fixture
def validator() -> HttpAuthSsoSessionValidator:
    return HttpAuthSsoSessionValidator(auth_playground_url=PLAYGROUND_URL)


@pytest.mark.asyncio
class TestHttpAuthSsoSessionValidator:
    @respx.mock
    async def test_should_return_session_claims_when_oauth2_proxy_accepts_session(self, validator: HttpAuthSsoSessionValidator):
        respx.get(url=AUTH_URL).mock(
            return_value=httpx.Response(
                status_code=202,
                headers={"X-Auth-Request-Email": "user@test.com", "X-Auth-Request-User": "user"},
            )
        )

        result = await validator.validate_session(session_cookie=SESSION_COOKIE)

        assert result.email == "user@test.com"
        assert result.user == "user"
        assert respx.calls.last.request.headers["cookie"] == SESSION_COOKIE

    @respx.mock
    async def test_should_return_invalid_oidc_token_error_when_session_is_expired(self, validator: HttpAuthSsoSessionValidator):
        respx.get(url=AUTH_URL).mock(return_value=httpx.Response(status_code=401))

        result = await validator.validate_session(session_cookie=SESSION_COOKIE)

        assert isinstance(result, InvalidOidcTokenError)

    @respx.mock
    async def test_should_return_invalid_oidc_token_error_when_email_header_is_missing(self, validator: HttpAuthSsoSessionValidator):
        respx.get(url=AUTH_URL).mock(return_value=httpx.Response(status_code=202, headers={}))

        result = await validator.validate_session(session_cookie=SESSION_COOKIE)

        assert isinstance(result, InvalidOidcTokenError)
        assert result.message == "No email in oauth2-proxy session"

    @respx.mock
    async def test_should_return_sso_provider_not_available_error_when_playground_is_unreachable(self, validator: HttpAuthSsoSessionValidator):
        respx.get(url=AUTH_URL).mock(side_effect=httpx.ConnectError("Connection refused"))

        result = await validator.validate_session(session_cookie=SESSION_COOKIE)

        assert isinstance(result, SsoProviderNotAvailableError)
