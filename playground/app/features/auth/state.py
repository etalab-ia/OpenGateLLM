from base64 import urlsafe_b64decode
import json
import time
from urllib.parse import quote

import httpx
from httpx import ConnectError, HTTPStatusError, TimeoutException
import reflex as rx

from app.core.configuration import configuration
from app.shared.components.toasts import httpx_error_toast


class AuthState(rx.State):
    """Authentication state."""

    # User information
    is_authenticated: bool = False
    user_id: int | None = None
    user_email: str | None = None
    user_name: str | None = None
    api_key: str | None = None
    api_key_id: int | None = None

    # Extended user info
    user_organization: int | None = None
    user_budget: float | None = None
    user_priority: int | None = None
    user_created: int | None = None
    user_updated: int | None = None
    user_permissions: list[str] = []
    user_limits: list[dict] = []

    # Loading state
    is_loading: bool = False
    auth_error_message: str = ""

    opengatellm_url: str = configuration.settings.playground_opengatellm_url
    opengatellm_timeout: int = configuration.settings.playground_opengatellm_timeout
    login_type: str = configuration.settings.auth_login_type
    playground_url: str | None = None if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_playground_url
    sso_logout_redirect_uri: str | None = None if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_logout_redirect_uri  # fmt: off
    sso_oidc_issuer_url: str | None = None if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_oidc_issuer_url

    # Form fields
    email_input: str = ""
    password_input: str = ""

    @rx.event
    def set_email_input(self, value: str):
        """Set email input value."""
        self.email_input = value

    @rx.event
    def set_password_input(self, value: str):
        """Set password input value."""
        self.password_input = value

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
            url=f"{self.opengatellm_url}/v1/me/info",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=self.opengatellm_timeout,
        )
        return response

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
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return json.loads(urlsafe_b64decode(payload_b64))

    @staticmethod
    def _token_is_expired(exp: int | None) -> bool:
        try:
            return bool(exp and exp < time.time())
        except Exception:
            return False

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
                # Create API key
                response = await self._password_login(client=client, email=email, password=password)
                response.raise_for_status()
                api_key = response.json().get("value")
                api_key_id = response.json().get("id")

                # Get user info
                response = await self._get_user_info(client=client, api_key=api_key)
                response.raise_for_status()

                user_data = response.json()

                # Update state
                self.is_authenticated = True
                self.auth_error_message = ""
                self.user_id = user_data.get("id")
                self.user_email = user_data.get("email")
                self.user_name = user_data.get("name")
                self.api_key = api_key
                self.api_key_id = api_key_id
                self.user_organization = user_data.get("organization")
                self.user_budget = user_data.get("budget")
                self.user_priority = user_data.get("priority", 0)
                self.user_created = user_data.get("created")
                self.user_updated = user_data.get("updated")
                self.user_permissions = user_data.get("permissions", [])
                self.user_limits = user_data.get("limits", [])

                yield rx.toast.success("Successfully logged in!", position="bottom-right")
                yield

                # Load models after successful login (if ChatState)
                if hasattr(self, "load_models"):
                    async for _ in self.load_models():
                        yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.is_loading = False
            yield

    @staticmethod
    def _parse_userinfo_response(response: httpx.Response) -> dict:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()

        text = response.text.strip()
        if text.count(".") == 2:
            return AuthState._decode_jwt_payload(text)
        return json.loads(text)

    async def _fetch_claims_from_userinfo(self, client: httpx.AsyncClient, access_token: str) -> dict:
        userinfo_url = f"{self.sso_oidc_issuer_url.rstrip('/')}/userinfo"
        response = await client.get(url=userinfo_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=self.opengatellm_timeout)
        response.raise_for_status()
        claims = self._parse_userinfo_response(response)

        return claims

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
        if self.is_authenticated:
            return

        headers = self.router.headers.raw_headers
        session_cookie = headers.get("cookie")
        if not session_cookie:
            yield self._redirect_to_status_page(route="/error", message="Session cookie not found in headers.")
            return

        id_token = None
        for key in ["authorization", "x-forwarded-id-token"]:
            id_token = self._oauth2_extract_token_from_headers(headers=headers, key=key)
            if id_token:
                break

        if not id_token:
            yield self._redirect_to_status_page(route="/error", message="ID token not found in headers.")
            return

        access_token = self._oauth2_extract_token_from_headers(headers=headers, key="x-auth-request-access-token")
        token_claims = self._decode_jwt_payload(id_token)
        sub = token_claims.get("sub")
        iss = token_claims.get("iss")
        exp = token_claims.get("exp")
        if not sub or not iss or exp is None:
            yield self._redirect_to_status_page(route="/error", message="Mandatory OIDC claims not found in ID token.")
            return
        if self._token_is_expired(exp):
            yield self.oidc_logout()
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
                        pass
                    case 401:  # SsoInvalidSessionHTTPException
                        yield self.oidc_logout()
                        return
                    case 403:  # SSOAccessDenied
                        yield self._redirect_to_status_page(route="/deny", message=self._http_error_detail(response))
                        return
                    case _:
                        yield self._redirect_to_status_page(route="/error", message=self._http_error_detail(response))
                        return

                api_key = response.json().get("value")
                api_key_id = response.json().get("id")

                response = await self._get_user_info(client=client, api_key=api_key)
                response.raise_for_status()
                user_data = response.json()

                self.is_authenticated = True
                self.auth_error_message = ""
                self.user_id = user_data.get("id")
                self.user_email = user_data.get("email")
                self.user_name = user_data.get("name")
                self.api_key = api_key
                self.api_key_id = api_key_id
                self.user_organization = user_data.get("organization")
                self.user_budget = user_data.get("budget")
                self.user_priority = user_data.get("priority", 0)
                self.user_created = user_data.get("created")
                self.user_updated = user_data.get("updated")
                self.user_permissions = user_data.get("permissions", [])
                self.user_limits = user_data.get("limits", [])

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
        self.user_organization = None
        self.user_budget = None
        self.user_priority = None
        self.user_created = None
        self.user_updated = None
        self.user_permissions = []
        self.user_limits = []

    @rx.event
    def oidc_logout(self):
        """Clear session and redirect the browser to oauth2-proxy sign_out.

        oauth2-proxy clears the session cookie then redirects to the provider logout URL.
        """
        self._clear_auth_state()
        sign_out_path = f"/oauth2/sign_out?rd={quote(self.sso_logout_redirect_uri, safe='')}"
        return rx.call_script(f"window.location.assign({json.dumps(sign_out_path)})")
