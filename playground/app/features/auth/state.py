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
    opengatellm_timeout: int = configuration.settings.playground_opengatellm_timeout
    sso_opengatellm_admin_api_key: str | None = configuration.settings.playground_sso_opengatellm_admin_api_key
    sso_opengatellm_default_role_id: int | None = configuration.settings.playground_sso_opengatellm_default_role_id

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

    async def _create_api_key(self, client: httpx.AsyncClient, email: str):
        response = await client.post(
            url=f"{self.opengatellm_url}/v1/admin/tokens",
            json={"email": email, "name": "playground"},
            headers={"Authorization": f"Bearer {self.sso_opengatellm_admin_api_key}"},
            timeout=self.opengatellm_timeout,
        )
        return response

    async def _create_user(self, client: httpx.AsyncClient, email: str):
        response = await client.post(
            url=f"{self.opengatellm_url}/v1/admin/users",
            json={"email": email, "name": email, "role": self.sso_opengatellm_default_role_id},
            headers={"Authorization": f"Bearer {self.sso_opengatellm_admin_api_key}"},
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
                api_key = response.json().get("key")
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

    @rx.event
    async def sso_login(self):
        if self.is_authenticated:
            return

        email = self.router.headers.raw_headers.get("x-forwarded-email")
        if not email:
            return

        self.is_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                # Create API key
                response = await self._create_api_key(client=client, email=email)

                if response.status_code == 404:
                    response = await self._create_user(client=client, email=email)
                    response.raise_for_status()

                    response = await self._create_api_key(client=client, email=email)
                    response.raise_for_status()

                response.raise_for_status()
                api_key = response.json().get("token")
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
