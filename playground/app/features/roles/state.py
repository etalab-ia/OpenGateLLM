from collections import defaultdict
import datetime as dt

import httpx
import reflex as rx

from app.features.roles.models import Role
from app.shared.states.entity_state import EntityState


class RolesState(EntityState):
    """Roles management state."""

    ############################################################
    # Load entities
    ############################################################
    entities: list[Role] = []
    router_owners: dict[int, str] = {}

    def _format_role(self, role: dict) -> Role:
        """Format role."""

        permissions_admin = True if "admin" in role["permissions"] else False
        permissions_create_public_collection = True if "create_public_collection" in role["permissions"] else False
        permissions_read_metric = True if "read_metric" in role["permissions"] else False
        permissions_provide_models = True if "provide_models" in role["permissions"] else False

        limits_dict = defaultdict(lambda: {"RPM": None, "RPD": None, "TPM": None, "TPD": None})

        for limit in role["limits"]:
            limits_dict[limit["router"]][limit["type"].upper()] = limit["value"]

        limits = [{"router": router, **limits} for router, limits in limits_dict.items()]

        return Role(
            id=role["id"],
            name=role["name"],
            permissions_admin=permissions_admin,
            permissions_create_public_collection=permissions_create_public_collection,
            permissions_read_metric=permissions_read_metric,
            permissions_provide_models=permissions_provide_models,
            limits=limits,
            users=role["users"],
            created=dt.datetime.fromtimestamp(role["created"]).strftime("%Y-%m-%d %H:%M"),
            updated=dt.datetime.fromtimestamp(role["updated"]).strftime("%Y-%m-%d %H:%M"),
        )

    @rx.var
    def roles(self) -> list[Role]:
        """Get roles list with correct typing for Reflex."""
        return self.entities

    @rx.event
    async def load_entities(self):
        """Load entities."""
        if not self.is_authenticated or not self.api_key:
            return

        self.entities_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/roles",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                response.raise_for_status()
                data = response.json()
                self.entities = []
                for role in data.get("data", []):
                    self.entities.append(self._format_role(role))

        except Exception as e:
            yield rx.toast.error(f"Error loading roles: {str(e)}", position="bottom-right")
        finally:
            self.entities_loading = False
            yield

    ############################################################
    # Delete entity
    ############################################################
    entity_to_delete: Role = Role()
    delete_limit_loading = False

    @rx.event
    def set_entity_to_delete(self, entity: Role):
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
            self.entity_to_delete = Role()

    async def delete_entity(self):
        """Delete a role."""
        self.delete_entity_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/admin/roles/{self.entity_to_delete.id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
                response.raise_for_status()

                self.handle_delete_entity_dialog_change(is_open=False)
                yield rx.toast.success("Role deleted successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield rx.toast.error(f"Error deleting role: {str(e)}", position="bottom-right")
        finally:
            self.delete_entity_loading = False
            yield

    ############################################################
    # Create entity
    ############################################################
    entity_to_create: Role = Role()

    @rx.event
    def set_new_entity_attribut(self, attribute: str, value: str | bool | None):
        """Set edit entity attributes."""
        if isinstance(value, str):
            setattr(self.entity_to_create, attribute, value.strip())
        else:
            setattr(self.entity_to_create, attribute, value)

    @rx.event
    async def create_entity(self):
        """Create a role."""
        if not self.entity_to_create.name:
            yield rx.toast.warning("Role name is required", position="bottom-right")
            return

        self.create_entity_loading = True
        yield

        permissions = []
        if self.entity_to_create.permissions_admin:
            permissions.append("admin")
        if self.entity_to_create.permissions_create_public_collection:
            permissions.append("create_public_collection")
        if self.entity_to_create.permissions_read_metric:
            permissions.append("read_metric")
        if self.entity_to_create.permissions_provide_models:
            permissions.append("provide_models")

        payload = {
            "name": self.entity_to_create.name,
            "permissions": permissions,
            "limits": self.entity_to_create.limits or [],
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/admin/roles",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
                response.raise_for_status()

                yield rx.toast.success("Role created successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield rx.toast.error(f"Error creating role: {str(e)}", position="bottom-right")
        finally:
            self.create_entity_loading = False
            yield

    ############################################################
    # Entity settings
    ############################################################
    entity: Role = Role()

    @rx.event
    def set_entity_settings(self, entity: Role):
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

    @rx.var
    def nb_permissions(self) -> int:
        """Get number of permissions."""
        count = 0
        if self.entity.permissions_admin:
            count += 1
        if self.entity.permissions_create_public_collection:
            count += 1
        if self.entity.permissions_read_metric:
            count += 1
        if self.entity.permissions_provide_models:
            count += 1

        return count

    @rx.event
    def handle_settings_entity_dialog_change(self, is_open: bool):
        """Handle settings dialog open/close state change."""
        if not is_open:
            self.entity = Role()

    @rx.event
    async def edit_entity(self):
        """Update a role."""
        self.edit_entity_loading = True
        yield

        permissions = []
        if self.entity.permissions_admin:
            permissions.append("admin")
        if self.entity.permissions_create_public_collection:
            permissions.append("create_public_collection")
        if self.entity.permissions_read_metric:
            permissions.append("read_metric")
        if self.entity.permissions_provide_models:
            permissions.append("provide_models")

        payload = {
            "name": self.entity.name,
            "permissions": permissions,
            "limits": self.entity.limits or [],
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/admin/roles/{self.entity.id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
            response.raise_for_status()

            self.handle_settings_entity_dialog_change(is_open=False)
            yield rx.toast.success("Role updated successfully", position="bottom-right")

            async for _ in self.load_entities():
                yield

        except Exception as e:
            yield rx.toast.error(f"Error updating role: {str(e)}", position="bottom-right")
        finally:
            self.edit_entity_loading = False
            yield
