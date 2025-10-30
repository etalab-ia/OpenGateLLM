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

    # Error message
    error_message: str = ""

    # Loading state
    is_loading: bool = False

    api_url: str = configuration.playground.api_url

    # Form fields
    email_input: str = ""
    password_input: str = ""

    @rx.event
    async def login_direct(self):
        """Handle login using direct state values."""
        email = self.email_input.strip()
        password = self.password_input.strip()

        if not email or not password:
            self.error_message = "Email and password are required"
            yield
            return

        self.is_loading = True
        self.error_message = ""
        yield

        try:
            async with httpx.AsyncClient() as client:
                # Login to get API key
                response = await client.post(f"{self.api_url}/v1/auth/login", json={"email": email, "password": password}, timeout=10.0)
                if response.status_code != 200:
                    error_detail = response.json().get("detail", "Login failed")
                    self.error_message = error_detail
                    self.is_loading = False
                    yield
                    return

                login_data = response.json()
                api_key = login_data.get("key")
                api_key_id = login_data.get("id")

                # Get user info
                response = await client.get(f"{self.api_url}/v1/me/info", headers={"Authorization": f"Bearer {api_key}"}, timeout=10.0)

                if response.status_code != 200:
                    self.error_message = "Failed to fetch user info"
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
                self.error_message = ""

                yield

                # Load models after successful login (if ChatState)
                if hasattr(self, "load_models"):
                    async for _ in self.load_models():
                        yield

        except httpx.TimeoutException:
            self.error_message = "Request timeout. Please check if the API is running."
        except httpx.ConnectError:
            self.error_message = f"Cannot connect to API at {self.api_url}. Please check the URL."
        except Exception as e:
            self.error_message = f"An error occurred: {str(e)}"
        finally:
            self.is_loading = False
            yield

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
        self.error_message = ""
