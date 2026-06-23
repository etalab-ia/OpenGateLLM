import httpx
import pytest
import respx

from api.domain.auth.errors import SsoProviderNotAvailableError
from api.infrastructure.http import HttpAuthSsoProviderClient

DEFAULT_ISSUER_URL = "http://my-test-issuer/"
DEFAULT_JWKS_URI = "http://my-test-issuer/jwks"
DEFAULT_JWKS = {"keys": [{"kid": "test-kid", "kty": "RSA", "use": "sig", "alg": "RS256"}]}


def client_factory(issuer_url: str = DEFAULT_ISSUER_URL) -> HttpAuthSsoProviderClient:
    return HttpAuthSsoProviderClient(issuer_url=issuer_url)


def discovery_url(issuer_url: str) -> str:
    return f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"


@pytest.mark.asyncio(loop_scope="session")
class TestHttpAuthSsoProviderClient:
    @respx.mock
    async def test_get_jwks_returns_jwks_when_oidc_discovery_succeeds(self):
        issuer_url = DEFAULT_ISSUER_URL
        discovery_route = respx.get(url=discovery_url(issuer_url)).mock(
            return_value=httpx.Response(
                status_code=200,
                json={"jwks_uri": DEFAULT_JWKS_URI},
                headers={"Content-Type": "application/json"},
            )
        )
        jwks_route = respx.get(url=DEFAULT_JWKS_URI).mock(
            return_value=httpx.Response(
                status_code=200,
                json=DEFAULT_JWKS,
                headers={"Content-Type": "application/json"},
            )
        )

        result = await client_factory().get_jwks(issuer_url=issuer_url)

        assert result == DEFAULT_JWKS
        assert discovery_route.called is True
        assert jwks_route.called is True

    @respx.mock
    async def test_get_jwks_strips_trailing_slash_from_issuer_url(self):
        issuer_url = "http://my-test-issuer/"
        discovery_route = respx.get(url="http://my-test-issuer/.well-known/openid-configuration").mock(
            return_value=httpx.Response(
                status_code=200,
                json={"jwks_uri": DEFAULT_JWKS_URI},
                headers={"Content-Type": "application/json"},
            )
        )
        jwks_route = respx.get(url=DEFAULT_JWKS_URI).mock(
            return_value=httpx.Response(
                status_code=200,
                json=DEFAULT_JWKS,
                headers={"Content-Type": "application/json"},
            )
        )

        result = await client_factory().get_jwks(issuer_url=issuer_url)

        assert result == DEFAULT_JWKS
        assert discovery_route.called is True
        assert jwks_route.called is True

    @respx.mock
    async def test_get_jwks_returns_error_when_jwks_uri_missing(self):
        issuer_url = DEFAULT_ISSUER_URL
        discovery_route = respx.get(url=discovery_url(issuer_url)).mock(
            return_value=httpx.Response(
                status_code=200,
                json={"issuer": issuer_url},
                headers={"Content-Type": "application/json"},
            )
        )

        result = await client_factory().get_jwks(issuer_url=issuer_url)

        assert result == SsoProviderNotAvailableError(message="No jwks_uri found in OIDC server metadata")
        assert discovery_route.called is True

    @respx.mock
    async def test_get_jwks_returns_error_when_discovery_returns_error_response(self):
        issuer_url = DEFAULT_ISSUER_URL
        discovery_route = respx.get(url=discovery_url(issuer_url)).mock(
            return_value=httpx.Response(
                status_code=503,
                text="service unavailable",
                headers={"Content-Type": "text/plain"},
            )
        )

        result = await client_factory().get_jwks(issuer_url=issuer_url)

        assert isinstance(result, SsoProviderNotAvailableError)
        assert result.message is not None
        assert "Error fetching JWKS:" in result.message
        assert discovery_route.called is True

    @respx.mock
    async def test_get_jwks_returns_error_when_jwks_fetch_returns_error_response(self):
        issuer_url = DEFAULT_ISSUER_URL
        discovery_route = respx.get(url=discovery_url(issuer_url)).mock(
            return_value=httpx.Response(
                status_code=200,
                json={"jwks_uri": DEFAULT_JWKS_URI},
                headers={"Content-Type": "application/json"},
            )
        )
        jwks_route = respx.get(url=DEFAULT_JWKS_URI).mock(
            return_value=httpx.Response(
                status_code=500,
                text="internal server error",
                headers={"Content-Type": "text/plain"},
            )
        )

        result = await client_factory().get_jwks(issuer_url=issuer_url)

        assert isinstance(result, SsoProviderNotAvailableError)
        assert result.message is not None
        assert "Error fetching JWKS:" in result.message
        assert discovery_route.called is True
        assert jwks_route.called is True

    @pytest.mark.parametrize(
        "exception",
        [
            httpx.TimeoutException("timeout"),
            httpx.ReadTimeout("read timeout"),
            httpx.ConnectTimeout("connect timeout"),
            httpx.WriteTimeout("write timeout"),
            httpx.PoolTimeout("pool timeout"),
            httpx.RemoteProtocolError("remote protocol error"),
            httpx.ConnectError("connect error"),
        ],
    )
    @respx.mock
    async def test_get_jwks_returns_error_when_request_fails(self, exception):
        issuer_url = DEFAULT_ISSUER_URL
        discovery_route = respx.get(url=discovery_url(issuer_url)).mock(side_effect=exception)

        result = await client_factory().get_jwks(issuer_url=issuer_url)

        assert isinstance(result, SsoProviderNotAvailableError)
        assert result.message is not None
        assert "Error fetching JWKS:" in result.message
        assert discovery_route.called is True
