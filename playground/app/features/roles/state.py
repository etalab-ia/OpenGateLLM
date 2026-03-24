from collections import defaultdict
import datetime as dt

import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.roles.models import Role
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState


class RolesState(EntityState):
    """Roles management state."""

    @rx.var
    def routers_name_list(self) -> list[str]:
        return sorted([router["name"] for router in self.routers_list])

    def _format_role(self, role: dict) -> Role:
        """Format role from OpenGateLLM format to Playground format."""

        router_dict_reverse = {v: k for k, v in self.routers_dict.items()}

        permissions_admin = True if "admin" in role["permissions"] else False
        permissions_create_public_collection = True if "create_public_collection" in role["permissions"] else False
        permissions_read_metric = True if "read_metric" in role["permissions"] else False
        permissions_provide_models = True if "provide_models" in role["permissions"] else False

        limits_dict = defaultdict(lambda: {"rpm": None, "rpd": None, "tpm": None, "tpd": None})

        for limit in role["limits"]:
            router_name = router_dict_reverse[limit["router"]]
            limits_dict[router_name][limit["type"]] = limit["value"]

        # Ensure limits are returned sorted by router name for consistent UI ordering
        limits = [{"router": router_name, **limits} for router_name, limits in sorted(limits_dict.items(), key=lambda x: x[0])]

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

    def _format_limit(self, limit: dict[str, str | int]) -> list[dict[str, str | int]]:
        """Format limit from Playground format to OpenGateLLM format."""
        return [
            {"router": self.routers_dict[limit["router"]], "type": "rpm", "value": limit["rpm"]},
            {"router": self.routers_dict[limit["router"]], "type": "rpd", "value": limit["rpd"]},
            {"router": self.routers_dict[limit["router"]], "type": "tpm", "value": limit["tpm"]},
            {"router": self.routers_dict[limit["router"]], "type": "tpd", "value": limit["tpd"]},
        ]

    ############################################################
    # Load entities
    ############################################################
    entities: list[Role] = []
    routers_list: list[dict[str, str | int]] = []
    routers_dict: dict[str, int] = {}

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

        response = None
        try:
            async with httpx.AsyncClient() as client:
                offset = 0
                limit = 100
                while True:
                    response = await client.get(
                        f"{self.opengatellm_url}/v1/admin/routers",
                        params={"offset": offset, "limit": limit},
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=configuration.settings.playground_opengatellm_timeout,
                    )

                    response.raise_for_status()
                    data = response.json()
                    routers_data = data.get("data", [])
                    self.routers_list = [{"id": router["id"], "name": router["name"]} for router in routers_data]
                    self.routers_dict = {router["name"]: router["id"] for router in routers_data}
                    offset += 100
                    if len(routers_data) < 100:
                        break

                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/roles",
                    params={
                        "offset": (self.page - 1) * self.per_page,
                        "limit": self.per_page,
                        "order_by": self.order_by_value,
                        "order_direction": self.order_direction_value,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )

                response.raise_for_status()
                data = response.json()
                self.entities = []
                for role in data.get("data", []):
                    self.entities.append(self._format_role(role))

            self.has_more_page = len(self.entities) == self.per_page

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
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

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/admin/roles/{self.entity_to_delete.id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                self.handle_delete_entity_dialog_change(is_open=False)
                yield rx.toast.success("Role deleted successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.delete_entity_loading = False
            yield

    async def delete_limit(self, role: Role, router: str):
        """Delete a limit for a role."""
        self.delete_limit_loading = True

        if not router:
            yield rx.toast.warning("Router is required", position="bottom-right")
            return

        current_limits = role.limits or []
        limits = []
        for limit in current_limits:
            if limit["router"] == router:
                continue

            limits.extend(
                [
                    {"router": self.routers_dict[limit["router"]], "type": "rpm", "value": limit["rpm"]},
                    {"router": self.routers_dict[limit["router"]], "type": "rpd", "value": limit["rpd"]},
                    {"router": self.routers_dict[limit["router"]], "type": "tpm", "value": limit["tpm"]},
                    {"router": self.routers_dict[limit["router"]], "type": "tpd", "value": limit["tpd"]},
                ]
            )

        yield

        payload = {"limits": limits}
        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/admin/roles/{role.id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                yield rx.toast.success("Limit deleted successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.delete_limit_loading = False
            yield

    ############################################################
    # Create entity
    ############################################################
    entity_to_create: Role = Role()

    new_limit: dict[str, int | str | None] = {"router": None, "rpm": None, "rpd": None, "tpm": None, "tpd": None}
    create_limit_loading = False

    @rx.event
    def set_create_limit_loading(self, loading: bool):
        """Set create limit loading."""
        self.create_limit_loading = loading

    @rx.event
    def set_new_limit_value(self, type: str, value: str | None):
        """Set new limit value."""
        if value is None:
            self.new_limit[type] = None
        elif type == "router":
            self.new_limit[type] = value
        else:
            self.new_limit[type] = int(value)

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

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/admin/roles",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                yield rx.toast.success("Role created successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.create_entity_loading = False
            yield

    @rx.event
    async def create_limit(self, role: Role):
        """Create limits for a role."""

        if not self.new_limit["router"]:
            yield rx.toast.warning("Router is required", position="bottom-right")
            return

        self.create_limit_loading = True
        yield

        current_limits = role.limits or []
        limits = []
        for limit in current_limits:
            if limit["router"] == self.new_limit["router"]:
                continue
            limits.extend(self._format_limit(limit))
        limits.extend(self._format_limit(self.new_limit))
        payload = {"limits": limits}
        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.opengatellm_url}/v1/admin/roles/{role.id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                self.new_limit = {"router": None, "rpm": None, "rpd": None, "tpm": None, "tpd": None}
                yield rx.toast.success("Limits added successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.create_limit_loading = False
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
    def permission_counters(self) -> dict[int, int]:
        """Get permission counters for all roles."""
        counters = {}
        for role in self.entities:
            count = 0
            if role.permissions_admin:
                count += 1
            if role.permissions_create_public_collection:
                count += 1
            if role.permissions_read_metric:
                count += 1
            if role.permissions_provide_models:
                count += 1
            counters[role.id] = count
        return counters

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

        limits = []
        for limit in self.entity.limits or []:
            limits.extend(self._format_limit(limit))

        payload = {"name": self.entity.name, "permissions": permissions, "limits": limits}

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/admin/roles/{self.entity.id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
            response.raise_for_status()

            self.handle_settings_entity_dialog_change(is_open=False)
            yield rx.toast.success("Role updated successfully", position="bottom-right")

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
    page: int = 1
    per_page: int = 20
    order_by_value: str = "id"
    order_direction: str = "asc"
    order_direction_options: list[str] = ["asc", "desc"]
    order_direction_value: str = "asc"
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
