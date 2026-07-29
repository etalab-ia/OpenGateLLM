import httpx

from api.domain.auth import AuthSsoSessionValidator
from api.domain.auth.errors import SsoInvalidSessionError, SsoProviderNotAvailableError


class HttpAuthSsoSessionValidator(AuthSsoSessionValidator):
    HTTP_TIMEOUT = 10.0

    def __init__(self, auth_playground_url: str):
        self.auth_url = f"{auth_playground_url.rstrip('/')}/oauth2/auth"

    async def validate_session(self, session_cookie: str) -> str | SsoInvalidSessionError | SsoProviderNotAvailableError:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=self.auth_url, headers={"Cookie": session_cookie}, timeout=self.HTTP_TIMEOUT)
        except Exception as exc:
            return SsoProviderNotAvailableError(message=f"Error validating oauth2-proxy session: {exc}")

        if response.status_code == 401:
            return SsoInvalidSessionError(message="Invalid or expired oauth2-proxy session")
        if response.status_code != 202:
            return SsoInvalidSessionError(message=f"Unexpected oauth2-proxy response: {response.status_code}")

        email = response.headers.get("X-Auth-Request-Email")
        if not email:
            return SsoInvalidSessionError(message="No email in oauth2-proxy session")

        return email
