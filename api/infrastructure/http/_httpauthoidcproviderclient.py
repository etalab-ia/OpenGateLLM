import httpx

from api.domain.auth import AuthOidcProviderClient
from api.domain.auth.errors import OidcProviderNotAvailableError


class HttpAuthOidcProviderClient(AuthOidcProviderClient):
    HTTP_TIMEOUT = 10.0

    def __init__(self, issuer_url: str):
        self.issuer_url = issuer_url

    async def get_jwks(self, issuer_url: str) -> dict | OidcProviderNotAvailableError:
        try:
            async with httpx.AsyncClient() as client:
                discovery_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
                response = await client.get(discovery_url, timeout=self.HTTP_TIMEOUT)
                response.raise_for_status()
                metadata = response.json()

                jwks_uri = metadata.get("jwks_uri")
                if not jwks_uri:
                    return OidcProviderNotAvailableError(message="No jwks_uri found in OIDC server metadata")

                response = await client.get(jwks_uri, timeout=self.HTTP_TIMEOUT)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            return OidcProviderNotAvailableError(message=f"Error fetching JWKS: {exc}")
