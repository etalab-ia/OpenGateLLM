from base64 import urlsafe_b64decode
import json
import time
from urllib.parse import quote

import httpx
from httpx import ConnectError, HTTPStatusError, TimeoutException
import reflex as rx

from app.core.configuration import configuration
from app.shared.components.toasts import httpx_error_toast

_userinfo_endpoints: dict[str, str] = {}


class AuthState(rx.State):
    """Authentication state."""

    # User information
    is_authenticated: bool = False
    user_id: int | None = None
    user_email: str | None = None
    user_name: str | None = None
    api_key: str | None = None
    api_key_id: int | None = None

    user_organization_id: int | None = None
    user_budget: float | None = None
    user_expires: int | None = None
    user_permissions: list[str] = []
    user_limits: list[dict] = []
    session_expiration: int | None = None

    # Loading state
    is_loading: bool = False
    auth_error_message: str = ""

    opengatellm_url: str = configuration.settings.playground_opengatellm_url
    opengatellm_timeout: int = configuration.settings.playground_opengatellm_timeout
    login_type: str = configuration.settings.auth_login_type
    sso_logout_redirect_uri: str | None = None if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_logout_redirect_uri  # fmt: off
    sso_oidc_issuer_url: str | None = None if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_oidc_issuer_url

    # Form fields
    email_input: str = ""
    password_input: str = ""

    async def _password_login(self, client: httpx.AsyncClient, email: str, password: str):
        response = await client.post(
            url=f"{self.opengatellm_url}/v1/auth/login",
            json={"email": email, "password": password},
            timeout=self.opengatellm_timeout,
        )
        return response

    async def _sso_login(self, client: httpx.AsyncClient, session_cookie: str, sub: str, iss: str, exp: int, claims: dict):
        response = await client.post(
            url=f"{self.opengatellm_url}/v1/auth/sso/login",
            headers={"Cookie": session_cookie},
            json={"sub": sub, "iss": iss, "exp": exp, "claims": claims},
            timeout=self.opengatellm_timeout,
        )
        return response

    async def _get_user_info(self, client: httpx.AsyncClient, api_key: str):
        response = await client.get(
            url=f"{self.opengatellm_url}/v1/me",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=self.opengatellm_timeout,
        )
        return response

    def _apply_session(self, user_data: dict, api_key: str, api_key_id: int, expires: int | None) -> None:
        self.is_authenticated = True
        self.auth_error_message = ""
        self.user_id = user_data.get("id")
        self.user_email = user_data.get("email")
        self.user_name = user_data.get("name")
        self.api_key = api_key
        self.api_key_id = api_key_id
        self.user_organization_id = user_data.get("organization_id")
        self.user_budget = user_data.get("budget")
        self.user_expires = user_data.get("expires")
        self.user_permissions = user_data.get("permissions", [])
        self.user_limits = user_data.get("limits", [])
        self.email_input = ""
        self.password_input = ""
        self.session_expiration = expires

    @staticmethod
    def _oauth2_extract_token_from_headers(headers: dict[str, str], key: str) -> str | None:
        value = headers.get(key)
        if not value:
            return None
        value = value.strip()
        if value.lower().startswith("bearer "):
            return value[7:].strip()
        return value

    @staticmethod
    def _decode_jwt_payload(token: str) -> dict:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT.")
        payload_b64 = parts[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(urlsafe_b64decode(payload_b64))
        if not isinstance(payload, dict):
            raise ValueError("Invalid JWT payload.")
        return payload

    @staticmethod
    def _token_is_expired(exp: int) -> bool:
        return exp < time.time()

    def _session_expired(self) -> bool:
        if self.session_expiration is None:
            return False
        return self._token_is_expired(self.session_expiration)

    def _expire_session(self):
        self._clear_auth_state()
        return rx.toast.warning("Your session has expired. Please log in again.", position="bottom-right")

    @rx.event
    def ensure_session(self):
        if self.is_authenticated and self._session_expired():
            return self._expire_session()

    @rx.event
    async def basic_login(self):
        email = self.email_input.strip()
        password = self.password_input.strip()

        if not email or not password:
            yield rx.toast.warning("Email and password are required", position="bottom-right")
            return

        self.is_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await self._password_login(client=client, email=email, password=password)
                response.raise_for_status()
                login_data = response.json()

                response = await self._get_user_info(client=client, api_key=login_data["value"])
                response.raise_for_status()
                user_data = response.json()
                self._apply_session(user_data=user_data, api_key=login_data["value"], api_key_id=login_data["id"], expires=login_data["expires"])
                yield
        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.is_loading = False
            yield

    async def _fetch_claims_from_userinfo(self, client: httpx.AsyncClient, access_token: str) -> dict:
        if not self.sso_oidc_issuer_url:
            raise ValueError("OIDC issuer URL is not configured.")

        issuer = self.sso_oidc_issuer_url.rstrip("/")
        userinfo_url = _userinfo_endpoints.get(issuer)
        if not userinfo_url:
            response = await client.get(url=f"{issuer}/.well-known/openid-configuration", timeout=self.opengatellm_timeout)
            response.raise_for_status()
            userinfo_url = response.json().get("userinfo_endpoint")
            if not isinstance(userinfo_url, str) or not userinfo_url:
                raise ValueError("userinfo_endpoint missing from OIDC discovery document.")
            _userinfo_endpoints[issuer] = userinfo_url

        response = await client.get(url=userinfo_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=self.opengatellm_timeout)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()

        text = response.text.strip()
        if text.count(".") == 2:
            return AuthState._decode_jwt_payload(text)
        return json.loads(text)

    @staticmethod
    def _http_error_detail(response: httpx.Response) -> str:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            return response.text
        if isinstance(detail, str):
            return detail
        return str(detail)

    def _redirect_to_status_page(self, route: str, message: str):
        self.auth_error_message = message
        return rx.redirect(route)

    @staticmethod
    def _exception_message(exception: Exception, response: httpx.Response | None) -> str:
        if isinstance(exception, TimeoutException):
            return "Request timeout"
        if isinstance(exception, ConnectError):
            return "Cannot connect to API"
        if isinstance(exception, HTTPStatusError) and response is not None:
            return AuthState._http_error_detail(response)
        return f"{type(exception).__name__}: {exception}"

    @rx.event
    async def oidc_login(self):
        headers = self.router.headers.raw_headers
        session_cookie = headers.get("cookie")
        if not session_cookie:
            yield self._redirect_to_status_page(route="/error", message="Session cookie not found in headers.")
            return

        id_token = self._oauth2_extract_token_from_headers(headers=headers, key="x-forwarded-id-token")
        if not id_token:
            yield self._redirect_to_status_page(route="/error", message="ID token not found in headers.")
            return

        access_token = self._oauth2_extract_token_from_headers(headers=headers, key="x-auth-request-access-token")
        if not access_token:
            yield self._redirect_to_status_page(route="/error", message="Access token not found in headers.")
            return

        try:
            token_claims = self._decode_jwt_payload(id_token)
        except Exception:
            yield self._redirect_to_status_page(route="/error", message="Invalid ID token.")
            return

        sub = token_claims.get("sub")
        iss = token_claims.get("iss")
        exp = token_claims.get("exp")
        if not sub or not iss or not isinstance(exp, int):
            yield self._redirect_to_status_page(route="/error", message="Mandatory OIDC claims not found in ID token.")
            return
        if self._token_is_expired(exp):
            yield self.oidc_logout()
            return
        if self.is_authenticated and self.session_expiration == exp:
            return

        self.is_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                access_claims = await self._fetch_claims_from_userinfo(client=client, access_token=access_token)
                response = await self._sso_login(client=client, session_cookie=session_cookie, sub=sub, iss=iss, exp=exp, claims=access_claims)
                match response.status_code:
                    case 200:
                        login_data = response.json()
                    case 401:  # SsoInvalidSessionHTTPException
                        yield self.oidc_logout()
                        return
                    case 403:  # SSOAccessDenied
                        yield self._redirect_to_status_page(route="/deny", message=self._http_error_detail(response))
                        return
                    case _:
                        yield self._redirect_to_status_page(route="/error", message=self._http_error_detail(response))
                        return

                response = await self._get_user_info(client=client, api_key=login_data["value"])
                response.raise_for_status()
                user_data = response.json()
                self._apply_session(user_data=user_data, api_key=login_data["value"], api_key_id=login_data["id"], expires=exp)

        except Exception as e:
            yield self._redirect_to_status_page(route="/error", message=self._exception_message(exception=e, response=response))
        finally:
            self.is_loading = False
            yield

    @rx.var
    def is_admin(self) -> bool:
        """Check if user has admin permission."""
        return "admin" in self.user_permissions

    @rx.event
    def password_logout(self):
        """Handle logout."""
        self._clear_auth_state()

    def _clear_auth_state(self):
        self.is_authenticated = False
        self.user_id = None
        self.user_email = None
        self.user_name = None
        self.api_key = None
        self.api_key_id = None
        self.user_organization_id = None
        self.user_budget = None
        self.user_expires = None
        self.user_permissions = []
        self.user_limits = []
        self.email_input = ""
        self.password_input = ""
        self.session_expiration = None

    @rx.event
    def oidc_logout(self):
        """Clear session and redirect the browser to oauth2-proxy sign_out.

        oauth2-proxy clears the session cookie then redirects to the provider logout URL.
        """
        self._clear_auth_state()
        sign_out_path = f"/oauth2/sign_out?rd={quote(self.sso_logout_redirect_uri, safe='')}"
        return rx.call_script(f"window.location.assign({json.dumps(sign_out_path)})")
