"""Account/user settings state management."""

import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.auth.state import AuthState
from app.shared.components.toasts import httpx_error_toast


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

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/me/info",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"current_password": self.current_password, "password": self.new_password},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                yield rx.toast.success("Password changed successfully!", position="bottom-right")
                self.current_password = ""
                self.new_password = ""
                self.confirm_password = ""

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
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
        if not self.edit_name or not self.edit_name.strip():
            yield rx.toast.warning("Name cannot be empty", position="bottom-right")
            return

        self.update_name_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/me/info",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"name": self.edit_name.strip()},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                self.user_name = self.edit_name.strip()
                yield rx.toast.success("Name updated successfully!", position="bottom-right")

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.update_name_loading = False
            yield

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
