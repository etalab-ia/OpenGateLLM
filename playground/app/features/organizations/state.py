import datetime as dt

import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.organizations.models import Organization
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState


class OrganizationsState(EntityState):
    """Organizations management state."""

    ############################################################
    # Load entities
    ############################################################
    entities: list[Organization] = []

    def _format_organization(self, organization: dict) -> Organization:
        """Format organization."""

        return Organization(
            id=organization["id"],
            name=organization["name"],
            users=organization["users"],
            created=dt.datetime.fromtimestamp(organization["created"]).strftime("%Y-%m-%d %H:%M"),
            updated=dt.datetime.fromtimestamp(organization["updated"]).strftime("%Y-%m-%d %H:%M"),
        )

    @rx.var
    def organizations(self) -> list[Organization]:
        """Get organizations list with correct typing for Reflex."""
        return self.entities

    @rx.event
    async def load_entities(self):
        """Load entities."""
        if not self.is_authenticated or not self.api_key:
            return

        self.entities_loading = True
        yield

        params = {
            "offset": (self.page - 1) * self.per_page,
            "limit": self.per_page,
            "order_by": self.order_by_value,
            "order_direction": self.order_direction_value,
        }

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url=f"{self.opengatellm_url}/v1/admin/organizations",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )

                response.raise_for_status()
                data = response.json()
                self.entities = []
                for organization in data.get("data", []):
                    self.entities.append(self._format_organization(organization))

            self.has_more_page = len(self.entities) == self.per_page

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.entities_loading = False
            yield

    ############################################################
    # Delete entity
    ############################################################
    entity_to_delete: Organization = Organization()

    @rx.event
    def set_entity_to_delete(self, entity: Organization):
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
            self.entity_to_delete = Organization()

    async def delete_entity(self):
        """Delete an organization."""
        self.delete_entity_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/admin/organizations/{self.entity_to_delete.id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                self.handle_delete_entity_dialog_change(is_open=False)
                yield rx.toast.success("Organization deleted successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.delete_entity_loading = False
            yield

    ############################################################
    # Create entity
    ############################################################
    entity_to_create: Organization = Organization()

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

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/admin/organizations",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                yield rx.toast.success("Organization created successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.create_entity_loading = False
            yield

    ############################################################
    # Entity settings
    ############################################################
    entity: Organization = Organization()

    @rx.event
    def set_entity_settings(self, entity: Organization):
        """Set entity settings."""
        self.entity = entity

    @rx.event
    def set_edit_entity_attribut(self, attribute: str, value: str | bool | None):
        """Set edit entity attributes."""
        if isinstance(value, str):
            setattr(self.entity, attribute, value.strip())
        else:
            setattr(self.entity, attribute, value)

    @rx.var
    def is_settings_entity_dialog_open(self) -> bool:
        """Check if settings dialog should be open."""
        return self.entity.id is not None

    @rx.event
    def handle_settings_entity_dialog_change(self, is_open: bool):
        """Handle settings dialog open/close state change."""
        if not is_open:
            self.entity = Organization()

    @rx.event
    async def edit_entity(self):
        """Update an organization."""
        self.edit_entity_loading = True
        yield

        payload = {"name": self.entity.name}

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/admin/organizations/{self.entity.id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
            response.raise_for_status()

            self.handle_settings_entity_dialog_change(is_open=False)
            yield rx.toast.success("Organization updated successfully", position="bottom-right")

            async for _ in self.load_entities():
                yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.edit_entity_loading = False
            yield

    ############################################################
    # Pagination & filters
    ############################################################
    per_page: int = 10
    order_by_options: list[str] = ["id", "name", "created", "updated"]

    @rx.event
    async def set_order_by(self, value: str):
        """Set order by field and reload."""
        self.order_by_value = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_entities():
            yield

    @rx.event
    async def set_order_direction(self, value: str):
        """Set order direction and reload."""
        self.order_direction_value = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_entities():
            yield

    @rx.event
    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            yield
            async for _ in self.load_entities():
                yield

    @rx.event
    async def next_page(self):
        if self.has_more_page:
            self.page += 1
            yield
            async for _ in self.load_entities():
                yield
