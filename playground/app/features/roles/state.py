"""Roles management state."""

import datetime

import httpx
import reflex as rx

from app.features.chat.state import ChatState
from app.features.roles.models import FormattedRole, Limit, Role


class RolesState(ChatState):
    """State for roles management."""

    # Roles list
    roles: list[Role] = []
    roles_loading: bool = False

    # Pagination for roles
    page: int = 1
    per_page: int = 5
    has_more_page: bool = False
    order_by: str = "id"
    order_direction: str = "asc"

    # Selected role for permissions
    permissions_selected_role_id: int | None = None
    permissions_selected_role_name: str = ""

    # Create role form
    new_role_name: str = ""
    new_role_permissions: list[str] = []
    create_role_loading: bool = False

    # Delete role
    role_to_delete: int | None = None
    delete_role_loading: bool = False

    # Edit role
    role_to_edit: int | None = None
    edit_role_name: str = ""
    edit_role_permissions: list[str] = []
    edit_role_loading: bool = False

    # Add limit form (per role)
    new_limit_router_name: str = ""
    new_limit_rpm: str = ""
    new_limit_rpd: str = ""
    new_limit_tpm: str = ""
    new_limit_tpd: str = ""
    add_limit_loading: bool = False

    # Delete limit
    delete_limit_loading: bool = False

    # Routers list for dropdown
    available_routers: list[dict[str, str | int]] = []
    routers_loading: bool = False
    router_id_to_name: dict[int, str] = {}
    router_name_to_id: dict[str, int] = {}

    @rx.var
    def roles_with_formatted_dates(self) -> list[FormattedRole]:
        """Get roles with formatted dates."""
        formatted = []
        for role in self.roles:
            formatted.append(
                FormattedRole(
                    id=role.id,
                    name=role.name,
                    permissions=[permission.replace("_", " ").capitalize() for permission in role.permissions],
                    limits=role.limits,
                    users=role.users,
                    created=datetime.datetime.fromtimestamp(role.created).strftime("%Y-%m-%d %H:%M"),
                    updated=datetime.datetime.fromtimestamp(role.updated).strftime("%Y-%m-%d %H:%M"),
                )
            )
        return formatted

    @rx.var
    def permissions_selected_role(self) -> Role | None:
        """Get the selected role for permissions."""
        if self.permissions_selected_role_id is None:
            return None
        for role in self.roles:
            if role.id == self.permissions_selected_role_id:
                return role
        return None

    @rx.var
    def roles_limits_by_router(self) -> dict[int, dict[str, dict[str, int | None]]]:
        """Get limits grouped by router name for each role. Returns dict[role_id][router_name][limit_type] = value."""
        result = {}
        for role in self.roles:
            role_limits = {}
            for limit in role.limits:
                router_name = self.router_id_to_name.get(limit.router, str(limit.router))
                if router_name not in role_limits:
                    role_limits[router_name] = {"rpm": None, "rpd": None, "tpm": None, "tpd": None}
                role_limits[router_name][limit.type.lower()] = limit.value
            result[role.id] = role_limits
        return result

    @rx.var
    def roles_routers_lists(self) -> dict[int, list[str]]:
        """Get list of router names for each role. Returns dict[role_id] = [router_names]."""
        result = {}
        for role in self.roles:
            routers_set = set()
            for limit in role.limits:
                router_name = self.router_id_to_name.get(limit.router, str(limit.router))
                routers_set.add(router_name)
            result[role.id] = sorted(list(routers_set))
        return result

    @rx.var
    def routers_list_for_dropdown(self) -> list[str]:
        """Get list of router names formatted for dropdown."""
        return [router["name"] for router in self.available_routers]

    @rx.var
    def is_delete_role_dialog_open(self) -> bool:
        """Check if delete role dialog should be open."""
        return self.role_to_delete is not None

    @rx.var
    def is_edit_role_dialog_open(self) -> bool:
        """Check if edit role dialog should be open."""
        return self.role_to_edit is not None

    # Event handlers
    @rx.event
    async def set_order_by(self, value: str):
        """Set order by field and reload."""
        self.order_by = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_roles():
            yield

    @rx.event
    async def set_order_direction(self, value: str):
        """Set order direction and reload."""
        self.order_direction = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_roles():
            yield

    @rx.event
    def set_new_role_name(self, value: str):
        """Set new role name."""
        self.new_role_name = value

    @rx.event
    def set_role_to_delete(self, role_id: int | None):
        """Set role to delete."""
        self.role_to_delete = role_id

    @rx.event
    def set_role_to_edit(self, role_id: int | None):
        """Set role to edit and load its data."""
        if role_id is None:
            self.role_to_edit = None
            self.edit_role_name = ""
            self.edit_role_permissions = []
        else:
            self.role_to_edit = role_id
            # Find role and populate edit form
            for role in self.roles:
                if role.id == role_id:
                    self.edit_role_name = role.name
                    self.edit_role_permissions = list(role.permissions)
                    break

    @rx.event
    def set_edit_role_name(self, value: str):
        """Set edit role name."""
        self.edit_role_name = value

    @rx.event
    def set_new_limit_router_name(self, value: str):
        """Set new limit router name."""
        self.new_limit_router_name = value

    @rx.event
    def set_new_limit_rpm(self, value: str):
        """Set new limit RPM value."""
        self.new_limit_rpm = value

    @rx.event
    def set_new_limit_rpd(self, value: str):
        """Set new limit RPD value."""
        self.new_limit_rpd = value

    @rx.event
    def set_new_limit_tpm(self, value: str):
        """Set new limit TPM value."""
        self.new_limit_tpm = value

    @rx.event
    def set_new_limit_tpd(self, value: str):
        """Set new limit TPD value."""
        self.new_limit_tpd = value

    @rx.event
    async def load_routers(self):
        """Load routers from API."""
        if not self.is_authenticated or not self.api_key:
            return

        self.routers_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/routers",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    routers_data = data.get("data", [])
                    self.available_routers = [{"id": r["id"], "name": r["name"]} for r in routers_data]
                    # Create bidirectional mapping
                    self.router_id_to_name = {r["id"]: r["name"] for r in routers_data}
                    self.router_name_to_id = {r["name"]: r["id"] for r in routers_data}
                else:
                    error_detail = response.json().get("detail", "Failed to load routers")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error loading routers: {str(e)}", position="bottom-right")
        finally:
            self.routers_loading = False
            yield

    @rx.event
    async def load_roles(self):
        """Load roles from API."""
        if not self.is_authenticated or not self.api_key:
            return

        # Load routers first if not already loaded
        if not self.available_routers:
            async for _ in self.load_routers():
                yield

        self.roles_loading = True
        yield

        try:
            params = {
                "offset": (self.page - 1) * self.per_page,
                "limit": self.per_page,
                "order_by": self.order_by,
                "order_direction": self.order_direction,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/roles",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code != 200:
                    error_detail = response.json().get("detail", "Failed to load roles")
                    yield rx.toast.error(str(error_detail), position="bottom-right")
                else:
                    data = response.json()
                    items = data.get("data", [])

                    self.roles = [
                        Role(
                            id=item["id"],
                            name=item["name"],
                            permissions=item["permissions"],
                            limits=[Limit(**lim) for lim in item["limits"]],
                            users=item.get("users", 0),
                            created=item["created"],
                            updated=item["updated"],
                        )
                        for item in items
                    ]
                    self.has_more_page = len(items) == self.per_page

        except Exception as e:
            yield rx.toast.error(f"Error loading roles: {str(e)}", position="bottom-right")
        finally:
            self.roles_loading = False
            yield

    def toggle_new_role_permission(self, permission: str, checked: bool):
        """Toggle a permission in the new role permissions list."""
        if checked and permission not in self.new_role_permissions:
            self.new_role_permissions.append(permission)
        elif not checked and permission in self.new_role_permissions:
            self.new_role_permissions.remove(permission)

    def toggle_edit_role_permission(self, permission: str, checked: bool):
        """Toggle a permission in the edit role permissions list."""
        if checked and permission not in self.edit_role_permissions:
            self.edit_role_permissions.append(permission)
        elif not checked and permission in self.edit_role_permissions:
            self.edit_role_permissions.remove(permission)

    @rx.event
    async def create_role(self):
        """Create a new role."""
        if not self.new_role_name.strip():
            yield rx.toast.warning("Role name is required", position="bottom-right")
            return

        self.create_role_loading = True
        yield

        try:
            payload = {
                "name": self.new_role_name.strip(),
                "permissions": self.new_role_permissions,
                "limits": [],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.opengatellm_url}/v1/admin/roles",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=60.0,
                )

                if response.status_code == 201:
                    self.new_role_name = ""
                    self.new_role_permissions = []
                    yield rx.toast.success("Role created successfully", position="bottom-right")
                    # Reload roles
                    async for _ in self.load_roles():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to create role")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.create_role_loading = False
            yield

    @rx.event
    async def delete_role(self, role_id: int):
        """Delete a role."""
        self.delete_role_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.opengatellm_url}/v1/admin/roles/{role_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    self.role_to_delete = None
                    yield rx.toast.success("Role deleted successfully", position="bottom-right")
                    # Reload roles
                    async for _ in self.load_roles():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to delete role")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.delete_role_loading = False
            yield

    @rx.event
    async def update_role(self):
        """Update a role name and permissions."""
        if self.role_to_edit is None:
            return

        if not self.edit_role_name.strip():
            yield rx.toast.warning("Role name is required", position="bottom-right")
            return

        self.edit_role_loading = True
        yield

        try:
            payload = {
                "name": self.edit_role_name.strip(),
                "permissions": self.edit_role_permissions,
            }

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.opengatellm_url}/v1/admin/roles/{self.role_to_edit}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    self.role_to_edit = None
                    yield rx.toast.success("Role updated successfully", position="bottom-right")
                    # Reload roles
                    async for _ in self.load_roles():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to update role")
                    if isinstance(error_detail, list) and len(error_detail) > 0:
                        first_error = error_detail[0]
                        if isinstance(first_error, dict):
                            yield rx.toast.error(first_error.get("msg", str(error_detail)), position="bottom-right")
                        else:
                            yield rx.toast.error(str(first_error), position="bottom-right")
                    else:
                        yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.edit_role_loading = False
            yield

    @rx.event
    async def add_limit(self, role_id: int):
        """Add limits for a router to a role (all 4 types at once)."""
        router_name = self.new_limit_router_name.strip()
        if not router_name:
            yield rx.toast.warning("Router is required", position="bottom-right")
            return

        # Convert router name to router ID
        router_id = self.router_name_to_id.get(router_name)
        if router_id is None:
            yield rx.toast.error(f"Router '{router_name}' not found", position="bottom-right")
            return

        # Parse and validate all 4 limit values
        limits_to_add = []
        limit_values = {
            "rpm": self.new_limit_rpm,
            "rpd": self.new_limit_rpd,
            "tpm": self.new_limit_tpm,
            "tpd": self.new_limit_tpd,
        }

        for limit_type, value_str in limit_values.items():
            if value_str.strip():
                try:
                    value = int(value_str)
                    if value < 0:
                        yield rx.toast.warning(f"{limit_type.upper()} value must be >= 0", position="bottom-right")
                        return
                    limits_to_add.append({
                        "router": router_id,
                        "type": limit_type,
                        "value": value,
                    })
                except ValueError:
                    yield rx.toast.warning(f"{limit_type.upper()} value must be a number", position="bottom-right")
                    return
            else:
                # Empty value means unlimited (None)
                limits_to_add.append({
                    "router": router_id,
                    "type": limit_type,
                    "value": None,
                })

        self.add_limit_loading = True
        yield

        try:
            # Get current role
            role = None
            for r in self.roles:
                if r.id == role_id:
                    role = r
                    break

            if role is None:
                yield rx.toast.error("Role not found", position="bottom-right")
                self.add_limit_loading = False
                yield
                return

            # Remove existing limits for this router, then add new ones
            new_limits = [{"router": lim.router, "type": lim.type, "value": lim.value} for lim in role.limits if lim.router != router_id]
            new_limits.extend(limits_to_add)

            payload = {"limits": new_limits}

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.opengatellm_url}/v1/admin/roles/{role_id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    self.new_limit_router_name = ""
                    self.new_limit_rpm = ""
                    self.new_limit_rpd = ""
                    self.new_limit_tpm = ""
                    self.new_limit_tpd = ""
                    yield rx.toast.success("Limits added successfully", position="bottom-right")
                    # Reload roles
                    async for _ in self.load_roles():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to add limits")
                    if isinstance(error_detail, list) and len(error_detail) > 0:
                        first_error = error_detail[0]
                        if isinstance(first_error, dict):
                            yield rx.toast.error(first_error.get("msg", str(error_detail)), position="bottom-right")
                        else:
                            yield rx.toast.error(str(first_error), position="bottom-right")
                    else:
                        yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.add_limit_loading = False
            yield

    @rx.event
    async def delete_router_limits(self, role_id: int, router_name: str):
        """Delete all limits for a specific router from a role."""
        # Convert router name to router ID
        router_id = self.router_name_to_id.get(router_name)
        if router_id is None:
            yield rx.toast.error(f"Router '{router_name}' not found", position="bottom-right")
            return

        self.delete_limit_loading = True
        yield

        try:
            # Get current role
            role = None
            for r in self.roles:
                if r.id == role_id:
                    role = r
                    break

            if role is None:
                yield rx.toast.error("Role not found", position="bottom-right")
                self.delete_limit_loading = False
                yield
                return

            # Remove all limits for this router
            new_limits = [{"router": lim.router, "type": lim.type, "value": lim.value} for lim in role.limits if lim.router != router_id]

            payload = {"limits": new_limits}

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.opengatellm_url}/v1/admin/roles/{role_id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    yield rx.toast.success("Limits deleted successfully", position="bottom-right")
                    # Reload roles
                    async for _ in self.load_roles():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to delete limits")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.delete_limit_loading = False
            yield

    @rx.event
    async def prev_page(self):
        """Go to previous page of roles."""
        if self.page > 1:
            self.page -= 1
            yield
            async for _ in self.load_roles():
                yield

    @rx.event
    async def next_page(self):
        """Go to next page of roles."""
        if self.has_more_page:
            self.page += 1
            yield
            async for _ in self.load_roles():
                yield
