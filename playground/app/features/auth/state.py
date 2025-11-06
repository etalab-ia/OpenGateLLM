"""Authentication state management."""

import httpx
import reflex as rx

from app.core.configuration import configuration


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
    user_created_at: int | None = None
    user_updated_at: int | None = None
    user_permissions: list[str] = []
    user_limits: list[dict] = []

    # Loading state
    is_loading: bool = False

    opengatellm_url: str = configuration.settings.playground_opengatellm_url

    # Form fields
    email_input: str = ""
    password_input: str = ""

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

        try:
            async with httpx.AsyncClient() as client:
                # Login to get API key
                response = await client.post(f"{self.opengatellm_url}/v1/auth/login", json={"email": email, "password": password}, timeout=10.0)
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
                response = await client.get(f"{self.opengatellm_url}/v1/me/info", headers={"Authorization": f"Bearer {api_key}"}, timeout=10.0)

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
                self.user_created_at = user_data.get("created_at")
                self.user_updated_at = user_data.get("updated_at")
                self.user_permissions = user_data.get("permissions", [])
                self.user_limits = user_data.get("limits", [])

                yield rx.toast.success("Successfully logged in!", position="bottom-right")
                yield

                # Load models after successful login (if ChatState)
                if hasattr(self, "load_models"):
                    async for _ in self.load_models():
                        yield

        except httpx.TimeoutException:
            yield rx.toast.error("Request timeout. Please check if the API is running.", position="bottom-right")
        except httpx.ConnectError:
            yield rx.toast.error(f"Cannot connect to API at {self.opengatellm_url}. Please check the URL.", position="bottom-right")
        except Exception as e:
            yield rx.toast.error(f"An error occurred: {str(e)}", position="bottom-right")
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
        self.user_created_at = None
        self.user_updated_at = None
        self.user_permissions = []
        self.user_limits = []
