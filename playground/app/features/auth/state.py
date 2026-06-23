from base64 import urlsafe_b64decode
import json
import time
from urllib.parse import quote

import httpx
from httpx import HTTPStatusError
import reflex as rx

from app.core.configuration import configuration
from app.shared.components.toasts import httpx_error_toast

UNAUTHORIZED_TOAST_DURATION_MS = 4_000


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
    has_access: bool = True

    opengatellm_url: str = configuration.settings.playground_opengatellm_url
    opengatellm_timeout: int = configuration.settings.playground_opengatellm_timeout
    login_type: str = configuration.settings.auth_login_type
    playground_url: str | None = None if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_playground_url
    sso_logout_redirect_uri: str | None = None if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_logout_redirect_uri  # fmt: off
    sso_oidc_issuer_url: str | None = None if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_oidc_issuer_url
    sso_name_claim_fields: list[str] = [] if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_name_claim_fields
    sso_groups_claim_field: str | None = None if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_groups_claim_field  # fmt: off
    sso_allowed_groups: list[str] = [] if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_allowed_groups
    sso_allowed_email_domains: list[str] = [] if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_allowed_email_domains  # fmt: off
    sso_organization_claim_field: str | None = None if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_organization_claim_field  # fmt: off
    sso_allowed_organizations: list[str] = [] if configuration.settings.auth_login_type != "oidc" else configuration.settings.auth_sso_allowed_organizations  # fmt: off

    @rx.var
    def oidc_login_progress_duration(self) -> str:
        """CSS duration for the OIDC login progress bar animation."""
        return rx.cond(
            self.has_access,
            f"{configuration.settings.playground_opengatellm_timeout}s",
            f"{UNAUTHORIZED_TOAST_DURATION_MS}ms",
        )

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

    async def _login(self, client: httpx.AsyncClient, email: str, password: str):
        response = await client.post(
            url=f"{self.opengatellm_url}/v1/auth/login",
            json={"email": email, "password": password},
            timeout=self.opengatellm_timeout,
        )
        return response

    async def _sso_login(self, client: httpx.AsyncClient, email: str, name: str | None, organization: str | None, token: str):
        response = await client.post(
            url=f"{self.opengatellm_url}/v1/auth/sso/login",
            json={"email": email, "name": name, "organization": organization, "token": token},
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
                response = await self._login(client=client, email=email, password=password)
                response.raise_for_status()
                api_key = response.json().get("value")
                api_key_id = response.json().get("id")

                # Get user info
                response = await self._get_user_info(client=client, api_key=api_key)
                response.raise_for_status()

                user_data = response.json()

                # Update state
                self.is_authenticated = True
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
    def _decode_jwt_payload(token: str) -> dict:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return json.loads(urlsafe_b64decode(payload_b64))

    @staticmethod
    def _token_is_expired(token: str) -> bool:
        try:
            claims = AuthState._decode_jwt_payload(token)
            exp = claims.get("exp")
            return bool(exp and exp < time.time())
        except Exception:
            return False

    @staticmethod
    def _name_from_claims(claims: dict, claim_fields: list[str]) -> str | None:
        if claim_fields:
            parts = [str(claims.get(field, "")).strip() for field in claim_fields]
            full_name = " ".join(part for part in parts if part)
            return full_name or None

        name = claims.get("name")
        if name is None:
            return None
        stripped_name = str(name).strip()
        return stripped_name or None

    @staticmethod
    def _check_user_access(
        organization: str | None,
        email: str,
        groups: list[str],
        allowed_groups: list[str],
        allowed_email_domains: list[str],
        allowed_organizations: list[str],
    ) -> bool:
        """
        Check SSO user access:
        - if all allowed_* are empty → everyone has access
        - if only one allowed_* is non-empty → that single criterion decides access
        - if at least two allowed_* are non-empty → OR across the enabled criteria
        """
        checks: list[bool] = []

        if allowed_groups:
            checks.append(any(group in allowed_groups for group in groups))

        if allowed_email_domains:
            checks.append(any(email.endswith(domain) for domain in allowed_email_domains))

        if allowed_organizations:
            checks.append(organization is not None and organization in allowed_organizations)

        return True if not checks else any(checks)

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

    def _oidc_reauth_redirect(self):
        """Clear stale oauth2-proxy session and restart OIDC login."""
        return_path = self.router.url.path or "/"
        sign_in_url = f"/oauth2/sign_in?rd={quote(return_path, safe='')}"
        sign_out_url = f"/oauth2/sign_out?rd={quote(sign_in_url, safe='')}"
        return rx.call_script(f"window.location.assign({json.dumps(sign_out_url)})")

    @rx.event
    async def oidc_login(self):
        """
        OIDC login logic:
        - if all allowed_* are empty → everyone has access
        - if only one allowed_* is non-empty → that single criterion decides access
        - if at least two allowed_* are non-empty → OR across the enabled criteria
        """
        if self.is_authenticated:
            return

        self.has_access = True
        headers = self.router.headers.raw_headers
        email = headers.get("x-auth-request-email")
        if not email:
            raise ValueError("Email not found in headers")

        id_token = None
        for key in ["authorization", "x-forwarded-id-token"]:
            id_token = self._oauth2_extract_token_from_headers(headers=headers, key=key)
            if id_token:
                break

        if not id_token:
            raise ValueError("ID token not found in headers")

        access_token = self._oauth2_extract_token_from_headers(headers=headers, key="x-auth-request-access-token")

        if self._token_is_expired(id_token):
            yield self._oidc_reauth_redirect()
            return

        self.is_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                # Create API key
                claims = await self._fetch_claims_from_userinfo(client=client, access_token=access_token)
                name = self._name_from_claims(claims=claims, claim_fields=self.sso_name_claim_fields)
                groups = claims.get(self.sso_groups_claim_field, [])
                organization = claims.get(self.sso_organization_claim_field)
                access_granted = self._check_user_access(
                    email=email,
                    organization=organization,
                    groups=groups,
                    allowed_groups=self.sso_allowed_groups,
                    allowed_email_domains=self.sso_allowed_email_domains,
                    allowed_organizations=self.sso_allowed_organizations,
                )
                self.has_access = access_granted

                if not self.has_access:
                    yield
                    yield rx.toast.error(
                        message="You are not authorized to access this application. Please contact your administrator.",
                        position="top-center",
                        duration=UNAUTHORIZED_TOAST_DURATION_MS,
                    )
                    sign_out_path = f"/oauth2/sign_out?rd={quote(self.sso_logout_redirect_uri, safe='')}"
                    yield rx.call_script(f"setTimeout(() => window.location.assign({json.dumps(sign_out_path)}), {UNAUTHORIZED_TOAST_DURATION_MS})")
                    return

                response = await self._sso_login(client=client, email=email, name=name, organization=organization, token=id_token)

                response.raise_for_status()
                api_key = response.json().get("value")
                api_key_id = response.json().get("id")

                # Get user info
                response = await self._get_user_info(client=client, api_key=api_key)
                response.raise_for_status()
                user_data = response.json()

                # Update state
                self.is_authenticated = True
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

        except HTTPStatusError as e:
            if response is not None and response.status_code == 401:
                yield self._oidc_reauth_redirect()
                return
            yield httpx_error_toast(exception=e, response=response)
        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.is_loading = False
            yield

    @rx.var
    def is_admin(self) -> bool:
        """Check if user has admin permission."""
        return "admin" in self.user_permissions

    @rx.var
    def is_master(self) -> bool:
        """Check if user is master."""
        return self.user_id == 0

    @rx.event
    def basic_logout(self):
        """Handle logout."""
        self.is_authenticated = False
        self.has_access = True
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
        """Handle SSO logout by redirecting the browser to oauth2-proxy sign_out.

        oauth2-proxy clears the session cookie then redirects to the provider logout URL.
        """
        self.is_authenticated = False
        self.has_access = True
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

        sign_out_path = f"/oauth2/sign_out?rd={quote(self.sso_logout_redirect_uri, safe='')}"
        return rx.call_script(f"window.location.assign({json.dumps(sign_out_path)})")
