"""Account/user settings state management."""

import httpx
import reflex as rx

from app.features.auth.state import AuthState


class AccountState(AuthState):
    """Account settings state."""

    # Update name form
    edit_name: str = ""
    update_name_loading: bool = False
    update_name_success: str = ""
    update_name_error: str = ""

    # Password change form
    current_password: str = ""
    new_password: str = ""
    confirm_password: str = ""
    password_change_loading: bool = False
    password_change_success: str = ""
    password_change_error: str = ""

    @rx.var
    def user_created_at_formatted(self) -> str:
        """Format created_at timestamp."""
        if self.user_created_at is None:
            return "N/A"
        import datetime

        return datetime.datetime.fromtimestamp(self.user_created_at).strftime("%Y-%m-%d %H:%M")

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
            self.password_change_error = "Current password is required"
            yield
            return

        if not self.new_password:
            self.password_change_error = "New password is required"
            yield
            return

        if len(self.new_password) < 8:
            self.password_change_error = "New password must be at least 8 characters"
            yield
            return

        if self.new_password != self.confirm_password:
            self.password_change_error = "Passwords do not match"
            yield
            return

        self.password_change_loading = True
        self.password_change_error = ""
        self.password_change_success = ""
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.api_url}/v1/me/info",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "current_password": self.current_password,
                        "password": self.new_password,
                    },
                    timeout=10.0,
                )

                if response.status_code == 204:
                    self.password_change_success = "Password changed successfully!"
                    # Clear form
                    self.current_password = ""
                    self.new_password = ""
                    self.confirm_password = ""
                else:
                    error_data = response.json()
                    self.password_change_error = error_data.get("detail", "Failed to change password")

        except httpx.TimeoutException:
            self.password_change_error = "Request timeout"
        except httpx.ConnectError:
            self.password_change_error = f"Cannot connect to API at {self.api_url}"
        except Exception as e:
            self.password_change_error = f"An error occurred: {str(e)}"
        finally:
            self.password_change_loading = False
            yield

    @rx.event
    def clear_password_messages(self):
        """Clear password change messages."""
        self.password_change_error = ""
        self.password_change_success = ""

    @rx.event
    def load_current_name(self):
        """Load current user name into edit field."""
        self.edit_name = self.user_name or ""

    @rx.event
    async def update_name(self):
        """Update user name."""
        # Validate input
        if not self.edit_name or not self.edit_name.strip():
            self.update_name_error = "Name cannot be empty"
            yield
            return

        self.update_name_loading = True
        self.update_name_error = ""
        self.update_name_success = ""
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.api_url}/v1/me/info",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"name": self.edit_name.strip()},
                    timeout=10.0,
                )

                if response.status_code == 204:
                    self.update_name_success = "Name updated successfully!"
                    # Update the user_name in state
                    self.user_name = self.edit_name.strip()
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
                            self.update_name_error = msg
                        else:
                            self.update_name_error = str(detail[0])
                    else:
                        self.update_name_error = str(detail)

        except httpx.TimeoutException:
            self.update_name_error = "Request timeout"
        except httpx.ConnectError:
            self.update_name_error = f"Cannot connect to API at {self.api_url}"
        except Exception as e:
            self.update_name_error = str(e)
        finally:
            self.update_name_loading = False
            yield

    @rx.event
    def clear_update_name_messages(self):
        """Clear name update messages."""
        self.update_name_error = ""
        self.update_name_success = ""

    @rx.event
    def clear_account_flash(self):
        """Clear transient success/error messages when (re)entering the page."""
        self.update_name_error = ""
        self.update_name_success = ""
        self.password_change_error = ""
        self.password_change_success = ""

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
