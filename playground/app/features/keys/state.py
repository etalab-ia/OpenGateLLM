"""API Keys management state."""

from datetime import datetime, timedelta
from typing import Any

import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.auth.state import AuthState
from app.features.keys.models import ApiKey, FormattedApiKey, Limit


class KeysState(AuthState):
    """API Keys management state."""

    # Keys list
    keys: list[ApiKey] = []
    keys_loading: bool = False

    # Pagination for keys
    keys_page: int = 1
    keys_limit: int = 10
    keys_total: int = 0
    keys_order_by: str = "id"
    keys_order_direction: str = "asc"

    # Create key form
    new_key_name: str = ""
    new_key_expires_date: str = ""  # Date in YYYY-MM-DD format
    create_key_loading: bool = False
    created_key: str = ""  # Store the created key to show once
    is_created_dialog_open: bool = False  # Explicit state for dialog

    # Delete confirmation
    key_to_delete: int | None = None
    delete_key_loading: bool = False

    @rx.var
    def is_delete_dialog_open(self) -> bool:
        """Check if delete dialog should be open."""
        return self.key_to_delete is not None

    @rx.var
    def min_expiry_date(self) -> str:
        """Get today's date as minimum for expiry date picker."""
        return datetime.now().strftime("%Y-%m-%d")

    @rx.var
    def max_expiry_date(self) -> str | None:
        """Get the maximum expiry date."""
        if configuration.settings.auth_key_max_expiration_days is not None:
            return (datetime.now() + timedelta(days=configuration.settings.auth_key_max_expiration_days)).strftime("%Y-%m-%d")

    @rx.var
    def formatted_limits(self) -> list[Limit]:
        """Get formatted limits from user data."""
        limits = []
        for limit_dict in self.user_limits:
            limits.append(
                Limit(
                    model=limit_dict.get("model", ""),
                    type=limit_dict.get("type", ""),
                    value=limit_dict.get("value"),
                )
            )
        return limits

    @rx.var
    def limits_by_model(self) -> dict[str, dict[str, int | None]]:
        """Group limits by model for table display."""
        result = {}
        for limit in self.formatted_limits:
            if limit.model not in result:
                result[limit.model] = {"rpm": None, "rpd": None, "tpm": None, "tpd": None}
            result[limit.model][limit.type.lower()] = limit.value
        return result

    @rx.var
    def models_list(self) -> list[str]:
        """Get list of models from limits."""
        return list(self.limits_by_model.keys())

    @rx.var
    def keys_with_formatted_dates(self) -> list[FormattedApiKey]:
        """Get keys with formatted dates."""
        formatted_keys = []
        for key in self.keys:
            formatted_keys.append(
                FormattedApiKey(
                    id=key.id,
                    name=key.name,
                    token=key.token,
                    created=datetime.fromtimestamp(key.created).strftime("%Y-%m-%d %H:%M"),
                    expires="Never" if key.expires is None else datetime.fromtimestamp(key.expires).strftime("%Y-%m-%d %H:%M"),
                )
            )
        return formatted_keys

    @rx.var
    def keys_total_pages(self) -> int:
        """Calculate total pages for keys."""
        if self.keys_total == 0:
            return 0
        return (self.keys_total + self.keys_limit - 1) // self.keys_limit

    @rx.var
    def has_more_keys(self) -> bool:
        """Check if there are more keys to load."""
        return self.keys_page < self.keys_total_pages

    @rx.event
    async def load_keys(self):
        """Load all API keys."""
        if not self.is_authenticated or not self.api_key:
            return

        self.keys_loading = True
        yield

        try:
            params = {
                "offset": (self.keys_page - 1) * self.keys_limit,
                "limit": self.keys_limit,
                "order_by": self.keys_order_by,
                "order_direction": self.keys_order_direction,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/me/keys",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                response.raise_for_status()
                data = response.json()
                keys_data = data.get("data", [])

                # Count before filtering for accurate pagination
                keys_count_before_filter = len(keys_data)
                self.keys = [ApiKey(**key) for key in keys_data if key["name"] != "playground"]

                # Estimate total (API doesn't return total, so we estimate)
                # Use the count before filtering to determine if there are more pages
                if keys_count_before_filter < self.keys_limit:
                    self.keys_total = (self.keys_page - 1) * self.keys_limit + len(self.keys)
                else:
                    self.keys_total = self.keys_page * self.keys_limit + 1

        except Exception as e:
            yield rx.toast.error(f"Error loading keys: {str(e)}", position="bottom-right")
            self.keys = []
        finally:
            self.keys_loading = False
            yield

    @rx.event
    async def create_key(self):
        """Create a new API key."""
        if not self.new_key_name.strip():
            yield rx.toast.warning("Key name is required", position="bottom-right")
            return

        self.create_key_loading = True
        self.created_key = ""
        yield

        try:
            payload: dict[str, Any] = {"name": self.new_key_name.strip()}

            # Add expires if provided
            if self.new_key_expires_date.strip():
                try:
                    # Convert date string (YYYY-MM-DD) to timestamp
                    date_obj = datetime.datetime.strptime(self.new_key_expires_date.strip(), "%Y-%m-%d")
                    # Set time to end of day (23:59:59)
                    date_obj = date_obj.replace(hour=23, minute=59, second=59)
                    expires_timestamp = int(date_obj.timestamp())
                    payload["expires"] = expires_timestamp
                except ValueError:
                    yield rx.toast.warning("Invalid date format", position="bottom-right")
                    self.create_key_loading = False
                    yield
                    return

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.opengatellm_url}/v1/me/keys",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=60.0,
                )

                if response.status_code == 201:
                    data = response.json()
                    self.created_key = data.get("key", "")
                    self.is_created_dialog_open = True
                    yield rx.toast.success("API key created successfully", position="bottom-right")
                    # Yield to update UI and show the dialog
                    yield
                    # Clear form
                    self.new_key_name = ""
                    self.new_key_expires_date = ""
                    # Reload keys
                    async for _ in self.load_keys():
                        yield
                else:
                    error_data = response.json()
                    detail = error_data.get("detail", "Failed to create key")

                    # Handle Pydantic validation errors (list format)
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

        except Exception as e:
            yield rx.toast.error(str(e), position="bottom-right")
        finally:
            self.create_key_loading = False
            yield

    @rx.event
    async def delete_key(self, key_id: int):
        """Delete an API key."""
        self.delete_key_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.opengatellm_url}/v1/me/keys/{key_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    self.key_to_delete = None
                    yield rx.toast.success("API key deleted successfully", position="bottom-right")
                    # Reload keys
                    async for _ in self.load_keys():
                        yield
                else:
                    error_data = response.json()
                    yield rx.toast.error(error_data.get("detail", "Failed to delete key"), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.delete_key_loading = False
            yield

    @rx.event
    def clear_created_key(self):
        """Clear the created key message."""
        self.created_key = ""
        self.is_created_dialog_open = False

    @rx.event
    def set_key_to_delete(self, key_id: int | None):
        """Set the key to delete."""
        self.key_to_delete = key_id

    @rx.event
    def handle_dialog_change(self, is_open: bool):
        """Handle dialog open/close state change."""
        if not is_open:
            self.key_to_delete = None

    @rx.event
    def handle_created_dialog_change(self, is_open: bool):
        """Handle created key dialog open/close state change."""
        self.is_created_dialog_open = is_open
        if not is_open:
            self.created_key = ""

    # Explicit setters to avoid deprecation of auto-setters in Reflex >=0.8.9
    @rx.event
    def set_new_key_name(self, value: str):
        self.new_key_name = value

    @rx.event
    def set_new_key_expires_date(self, value: str):
        self.new_key_expires_date = value

    @rx.event
    async def set_keys_order_by(self, value: str):
        """Set order by field and reload."""
        self.keys_order_by = value
        self.keys_page = 1
        yield
        async for _ in self.load_keys():
            yield

    @rx.event
    async def set_keys_order_direction(self, value: str):
        """Set order direction and reload."""
        self.keys_order_direction = value
        self.keys_page = 1
        yield
        async for _ in self.load_keys():
            yield

    @rx.event
    async def prev_keys_page(self):
        """Go to previous page of keys."""
        if self.keys_page > 1:
            self.keys_page -= 1
            yield
            async for _ in self.load_keys():
                yield

    @rx.event
    async def next_keys_page(self):
        """Go to next page of keys."""
        if self.has_more_keys:
            self.keys_page += 1
            yield
            async for _ in self.load_keys():
                yield
