import datetime as dt

import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.keys.models import Key
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState


class KeysState(EntityState):
    """API keys management state."""

    ############################################################
    # Load entities
    ############################################################
    entities: list[Key] = []

    def _format_key(self, key: dict) -> Key:
        """Format key."""

        return Key(
            id=key["id"],
            name=key["name"],
            token=key["token"],
            expires=dt.datetime.fromtimestamp(key["expires"]).strftime("%Y-%m-%d %H:%M") if key["expires"] else "never",
            created=dt.datetime.fromtimestamp(key["created"]).strftime("%Y-%m-%d %H:%M"),
        )

    @rx.var
    def keys(self) -> list[Key]:
        """Get keys list with correct typing for Reflex."""
        return self.entities

    @rx.event(background=True)
    async def load_entities(self):
        """Load entities."""
        async with self:
            if not self.is_authenticated or not self.api_key:
                return
            self.entities_loading = True
            url = self.opengatellm_url
            api_key = self.api_key
            page = self.page
            per_page = self.per_page
            order_by = self.order_by_value
            order_direction = self.order_direction_value
            yield

        params = {
            "offset": (page - 1) * per_page,
            "limit": per_page,
            "order_by": order_by,
            "order_direction": order_direction,
        }

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url=f"{url}/v1/me/keys",
                    params=params,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()
                data = response.json()
                entities = [
                    Key(
                        id=k["id"],
                        name=k["name"],
                        token=k["token"],
                        expires=dt.datetime.fromtimestamp(k["expires"]).strftime("%Y-%m-%d %H:%M") if k["expires"] else "never",
                        created=dt.datetime.fromtimestamp(k["created"]).strftime("%Y-%m-%d %H:%M"),
                    )
                    for k in data.get("data", [])
                    if k["name"] != "playground"
                ]
            has_more = len(entities) == per_page
            async with self:
                self.entities = entities
                self.has_more_page = has_more
                yield
        except Exception as e:
            async with self:
                yield httpx_error_toast(exception=e, response=response)
        finally:
            async with self:
                self.entities_loading = False
                yield

    ############################################################
    # Delete entity
    ############################################################
    entity_to_delete: Key = Key()

    @rx.event
    def set_entity_to_delete(self, entity: Key):
        """Set entity to delete."""
        self.entity_to_delete = entity

    @rx.var
    def is_delete_entity_dialog_open(self) -> bool:
        """Check if delete dialog should be open."""
        return self.entity_to_delete.id is not None

    @rx.event
    def handle_delete_entity_dialog_change(self, is_open: bool):
        """Handle delete entity dialog open/close state change."""
        if not is_open:
            self.entity_to_delete = Key()

    async def delete_entity(self):
        """Delete a key."""
        self.delete_entity_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/me/keys/{self.entity_to_delete.id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                self.handle_delete_entity_dialog_change(is_open=False)
                yield rx.toast.success("Key deleted successfully", position="bottom-right")
                yield type(self).load_entities()

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.delete_entity_loading = False
            yield

    ############################################################
    # Create entity
    ############################################################
    entity_to_create: Key = Key()
    is_created_dialog_open: bool = False
    created_key: str = ""  # Store the created key to show once

    @rx.event
    def clear_created_key(self):
        """Clear the created key message."""
        self.created_key = ""
        self.is_created_dialog_open = False

    @rx.event
    def handle_created_dialog_change(self, is_open: bool):
        """Handle created key dialog open/close state change."""
        self.is_created_dialog_open = is_open
        if not is_open:
            self.created_key = ""

    @rx.var
    def min_expiry_date(self) -> str:
        """Get today's date as minimum for expiry date picker."""
        return dt.datetime.now().strftime("%Y-%m-%d")

    @rx.var
    def max_expiry_date(self) -> str:
        """Get the maximum expiry date."""
        if configuration.settings.auth_key_max_expiration_days is not None:
            return (dt.datetime.now() + dt.timedelta(days=configuration.settings.auth_key_max_expiration_days - 1)).strftime("%Y-%m-%d")
        return ""

    @rx.event
    def set_new_entity_attribut(self, attribute: str, value: str | bool | None):
        """Set new entity attributes."""
        if isinstance(value, str):
            setattr(self.entity_to_create, attribute, value.strip())
        else:
            setattr(self.entity_to_create, attribute, value)

    @rx.event
    async def create_entity(self):
        """Create a user."""
        if not self.entity_to_create.name:
            yield rx.toast.warning("Name is required", position="bottom-right")
            return

        self.create_entity_loading = True
        yield

        payload = {"name": self.entity_to_create.name}

        if self.entity_to_create.expires:
            expires = dt.datetime.strptime(self.entity_to_create.expires, "%Y-%m-%d").timestamp()
            payload["expires"] = expires

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/me/keys",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()
                data = response.json()

                # Store the created key to display in dialog
                self.created_key = data.get("key", "")
                self.is_created_dialog_open = True

                yield rx.toast.success("Key created successfully", position="bottom-right")
                yield type(self).load_entities()

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.create_entity_loading = False
            yield

    ############################################################
    # Pagination & filters
    ############################################################
    page: int = 1
    per_page: int = 20
    order_by_value: str = "id"
    order_direction: str = "asc"
    order_direction_options: list[str] = ["asc", "desc"]
    order_direction_value: str = "asc"
    order_by_options: list[str] = ["id", "name", "created"]

    @rx.event(background=True)
    async def set_order_by(self, value: str):
        """Set order by field and reload."""
        async with self:
            self.order_by_value = value
            self.page = 1
            self.has_more_page = False
            yield type(self).load_entities()

    @rx.event(background=True)
    async def set_order_direction(self, value: str):
        """Set order direction and reload."""
        async with self:
            self.order_direction_value = value
            self.page = 1
            self.has_more_page = False
            yield type(self).load_entities()

    @rx.event(background=True)
    async def prev_page(self):
        async with self:
            if self.page > 1:
                self.page -= 1
                yield type(self).load_entities()

    @rx.event(background=True)
    async def next_page(self):
        async with self:
            if self.has_more_page:
                self.page += 1
                yield type(self).load_entities()
