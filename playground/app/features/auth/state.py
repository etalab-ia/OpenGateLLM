import httpx
import reflex as rx

from app.core.configuration import configuration
from app.shared.components.toasts import httpx_error_toast


class AuthState(rx.State):
    """Authentication state."""

    # User information

    is_authenticated: bool = False
    user_id: int | None = None
    user_email: str
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

    opengatellm_url: str = configuration.settings.playground_opengatellm_url
    admin_api_key: str = configuration.settings.playground_admin_api_key
    default_role_id: int = int(configuration.settings.playground_default_role_id)

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

    @rx.event
    async def login_proconnect(self):
        """Auto-login using the ProConnect identity injected by oauth2-proxy.

        Reads the X-Auth-Request-Email header forwarded by oauth2-proxy into the WebSocket
        connection. If the header is present, calls POST /v1/auth/proconnect on the API
        (no password required - the OIDC authentication already happened at the proxy level).
        If the header is absent the user landed directly on the playground (port 8501) and
        no action is taken - they can still log in with email/password.
        """
        if self.is_authenticated:
            return

        # oauth2-proxy injecte X-Forwarded-Email (via pass_user_headers=true)
        # accessible via raw_headers (clés en minuscules avec tirets)
        email = self.router.headers.raw_headers.get("x-forwarded-email")
        if not email:
            return

        self.is_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                # response = await client.post(
                #     f"{self.opengatellm_url}/v1/auth/proconnect",
                #     headers={"X-Auth-Request-Email": email},
                #     timeout=configuration.settings.playground_opengatellm_timeout,
                # )
                import requests

                url = f"{self.opengatellm_url}/v1/admin/users"
                response = requests.get(url=url, params={"email": email}, headers={"Authorization": f"Bearer {self.admin_api_key}"})
                if response.status_code == 404:
                    # TODO:  rendre le password optionnel
                    response = requests.post(
                        url=url,
                        json={"email": email, "name": email, "password": "changeme", "role": self.default_role_id},
                        headers={"Authorization": f"Bearer {self.admin_api_key}"},
                    )
                    if response.status_code != 201:
                        error_detail = response.json().get("detail", "Failed to create user")
                        error_detail = f"Failed to create user: {error_detail}\nURL: {url}\nAPI Key: {self.admin_api_key}"
                        yield rx.toast.error(error_detail, position="bottom-right")
                        self.is_loading = False
                        yield
                        return

                    user_id = response.json().get("id")

                elif response.status_code == 200:
                    user_id = response.json().get("data", [])[0]["id"]
                else:
                    error_detail = response.json().get("detail", "Failed to fetch user info")
                    error_detail = f"Failed to fetch user info: {error_detail}\nURL: {url}\nAPI Key: {self.admin_api_key}"

                    yield rx.toast.error(error_detail, position="bottom-right")
                    self.is_loading = False
                    yield
                    return

                # TODO: support email as param to /v1/admin/tokens endpoint
                # TODO: add SSO expiration duration
                response = requests.post(
                    url=f"{self.opengatellm_url}/v1/admin/tokens",
                    json={"user": user_id, "name": "playground"},
                    headers={"Authorization": f"Bearer {self.admin_api_key}"},
                )
                if response.status_code != 201:
                    error_detail = response.json().get("detail", "Failed to create token")
                    error_detail = f"Failed to create token: {error_detail}\nURL: {url}\nAPI Key: {self.admin_api_key}"
                    yield rx.toast.error(error_detail, position="bottom-right")
                    self.is_loading = False
                    yield
                    return

                api_key = response.json().get("token")
                api_key_id = response.json().get("id")

                response = await client.get(
                    f"{self.opengatellm_url}/v1/me/info",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )

                if response.status_code != 200:
                    yield rx.toast.error("Failed to fetch user info", position="bottom-right")
                    self.is_loading = False
                    yield
                    return

                user_data = response.json()

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

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.is_loading = False
            yield

    @rx.event
    async def login_direct(self):
        """Handle login using direct state values."""
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
                # Login to get API key
                response = await client.post(
                    f"{self.opengatellm_url}/v1/auth/login",
                    json={"email": email, "password": password},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                if response.status_code != 200:
                    error_detail = response.json().get("detail", "Login failed")
                    yield rx.toast.error(error_detail, position="bottom-right")
                    self.is_loading = False
                    yield
                    return

                login_data = response.json()
                api_key = login_data.get("key")
                api_key_id = login_data.get("id")

                # Get user info
                response = await client.get(
                    f"{self.opengatellm_url}/v1/me/info",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )

                if response.status_code != 200:
                    yield rx.toast.error("Failed to fetch user info", position="bottom-right")
                    self.is_loading = False
                    yield
                    return

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

    @rx.var
    def is_admin(self) -> bool:
        """Check if user has admin permission."""
        return "admin" in self.user_permissions

    @rx.var
    def is_master(self) -> bool:
        """Check if user is master."""
        return self.user_id == 0

    @rx.event
    def logout(self):
        """Handle logout."""
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
