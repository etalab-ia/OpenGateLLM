"""Account/user settings state management."""

import httpx
import reflex as rx

from app.features.auth.state import AuthState


class AccountState(AuthState):
    """Account settings state."""

    # Update name form
    edit_name: str = ""
    update_name_loading: bool = False

    # Password change form
    current_password: str = ""
    new_password: str = ""
    confirm_password: str = ""
    password_change_loading: bool = False

    @rx.var
    def user_created_formatted(self) -> str:
        """Format created timestamp."""
        if self.user_created is None:
            return "N/A"
        import datetime

        return datetime.datetime.fromtimestamp(self.user_created).strftime("%Y-%m-%d %H:%M")

    @rx.var
    def user_budget_formatted(self) -> str:
        """Format budget, showing 'Unlimited' if None."""
        if self.user_budget is None:
            return "Unlimited"
        return str(self.user_budget)

    @rx.event
    async def change_password(self):
        """Change user password."""
        # Validate inputs
        if not self.current_password:
            yield rx.toast.warning("Current password is required", position="bottom-right")
            return

        if not self.new_password:
            yield rx.toast.warning("New password is required", position="bottom-right")
            return

        if len(self.new_password) < 8:
            yield rx.toast.warning("New password must be at least 8 characters", position="bottom-right")
            return

        if self.new_password != self.confirm_password:
            yield rx.toast.warning("Passwords do not match", position="bottom-right")
            return

        self.password_change_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.opengatellm_url}/v1/me/info",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "current_password": self.current_password,
                        "password": self.new_password,
                    },
                    timeout=60.0,
                )

                if response.status_code == 204:
                    yield rx.toast.success("Password changed successfully!", position="bottom-right")
                    # Clear form
                    self.current_password = ""
                    self.new_password = ""
                    self.confirm_password = ""
                else:
                    error_data = response.json()
                    yield rx.toast.error(error_data.get("detail", "Failed to change password"), position="bottom-right")

        except httpx.TimeoutException:
            yield rx.toast.error("Request timeout", position="bottom-right")
        except httpx.ConnectError:
            yield rx.toast.error(f"Cannot connect to API at {self.opengatellm_url}", position="bottom-right")
        except Exception as e:
            yield rx.toast.error(f"An error occurred: {str(e)}", position="bottom-right")
        finally:
            self.password_change_loading = False
            yield

    @rx.event
    def load_current_name(self):
        """Load current user name into edit field."""
        self.edit_name = self.user_name or ""

    @rx.event
    async def update_name(self):
        """Update user name."""
        # Validate input
        if not self.edit_name or not self.edit_name.strip():
            yield rx.toast.warning("Name cannot be empty", position="bottom-right")
            return

        self.update_name_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.opengatellm_url}/v1/me/info",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"name": self.edit_name.strip()},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    # Update the user_name in state
                    self.user_name = self.edit_name.strip()
                    yield rx.toast.success("Name updated successfully!", position="bottom-right")
                else:
                    error_data = response.json()
                    detail = error_data.get("detail", "Failed to update name")

                    # Handle Pydantic validation errors
                    if isinstance(detail, list) and len(detail) > 0:
                        first_error = detail[0]
                        if isinstance(first_error, dict):
                            msg = first_error.get("msg", "Validation error")
                            if ", " in msg:
                                msg = msg.split(", ", 1)[1]
                            yield rx.toast.error(msg, position="bottom-right")
                        else:
                            yield rx.toast.error(str(detail[0]), position="bottom-right")
                    else:
                        yield rx.toast.error(str(detail), position="bottom-right")

        except httpx.TimeoutException:
            yield rx.toast.error("Request timeout", position="bottom-right")
        except httpx.ConnectError:
            yield rx.toast.error(f"Cannot connect to API at {self.opengatellm_url}", position="bottom-right")
        except Exception as e:
            yield rx.toast.error(str(e), position="bottom-right")
        finally:
            self.update_name_loading = False
            yield

    # Explicit setters to avoid deprecation of auto-setters in Reflex >=0.8.9
    @rx.event
    def set_edit_name(self, value: str):
        self.edit_name = value

    @rx.event
    def set_current_password(self, value: str):
        self.current_password = value

    @rx.event
    def set_new_password(self, value: str):
        self.new_password = value

    @rx.event
    def set_confirm_password(self, value: str):
        self.confirm_password = value
