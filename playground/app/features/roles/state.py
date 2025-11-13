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
    roles_page: int = 1
    roles_limit: int = 10
    roles_total: int = 0
    roles_order_by: str = "id"
    roles_order_direction: str = "asc"

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
    new_limit_model: str = ""
    new_limit_rpm: str = ""
    new_limit_rpd: str = ""
    new_limit_tpm: str = ""
    new_limit_tpd: str = ""
    add_limit_loading: bool = False

    # Delete limit
    delete_limit_loading: bool = False

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
    def roles_limits_by_model(self) -> dict[int, dict[str, dict[str, int | None]]]:
        """Get limits grouped by model for each role. Returns dict[role_id][model][limit_type] = value."""
        result = {}
        for role in self.roles:
            role_limits = {}
            for limit in role.limits:
                if limit.model not in role_limits:
                    role_limits[limit.model] = {"rpm": None, "rpd": None, "tpm": None, "tpd": None}
                role_limits[limit.model][limit.type.lower()] = limit.value
            result[role.id] = role_limits
        return result

    @rx.var
    def roles_models_lists(self) -> dict[int, list[str]]:
        """Get list of models for each role. Returns dict[role_id] = [models]."""
        result = {}
        for role in self.roles:
            models_set = set()
            for limit in role.limits:
                models_set.add(limit.model)
            result[role.id] = sorted(list(models_set))
        return result

    @rx.var
    def roles_total_pages(self) -> int:
        """Calculate total pages for roles."""
        if self.roles_total == 0:
            return 0
        return (self.roles_total + self.roles_limit - 1) // self.roles_limit

    @rx.var
    def has_more_roles(self) -> bool:
        """Check if there are more roles to load."""
        return self.roles_page < self.roles_total_pages

    @rx.var
    def is_delete_role_dialog_open(self) -> bool:
        """Check if delete role dialog should be open."""
        return self.role_to_delete is not None

    @rx.var
    def is_edit_role_dialog_open(self) -> bool:
        """Check if edit role dialog should be open."""
        return self.role_to_edit is not None

    @rx.var
    def roles_list_for_dropdown(self) -> list[dict[str, str | int]]:
        """Get list of roles formatted for dropdown."""
        return [{"label": role.name, "value": str(role.id)} for role in self.roles]

    # Event handlers
    @rx.event
    async def set_roles_order_by(self, value: str):
        """Set order by field and reload."""
        self.roles_order_by = value
        self.roles_page = 1
        yield
        async for _ in self.load_roles():
            yield

    @rx.event
    async def set_roles_order_direction(self, value: str):
        """Set order direction and reload."""
        self.roles_order_direction = value
        self.roles_page = 1
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
    def set_new_limit_model(self, value: str):
        """Set new limit model."""
        self.new_limit_model = value

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
    async def load_roles(self):
        """Load roles from API."""
        if not self.is_authenticated or not self.api_key:
            return

        self.roles_loading = True
        yield

        try:
            params = {
                "offset": (self.roles_page - 1) * self.roles_limit,
                "limit": self.roles_limit,
                "order_by": self.roles_order_by,
                "order_direction": self.roles_order_direction,
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
                    roles_data = data.get("data", [])
                    self.roles = [
                        Role(
                            id=r["id"],
                            name=r["name"],
                            permissions=r["permissions"],
                            limits=[Limit(**lim) for lim in r["limits"]],
                            users=r.get("users", 0),
                            created=r["created"],
                            updated=r["updated"],
                        )
                        for r in roles_data
                    ]
                    # Estimate total (API doesn't return total, so we estimate)
                    if len(self.roles) < self.roles_limit:
                        self.roles_total = (self.roles_page - 1) * self.roles_limit + len(self.roles)
                    else:
                        self.roles_total = self.roles_page * self.roles_limit + 1

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
        """Add limits for a model to a role (all 4 types at once)."""
        if not self.new_limit_model.strip():
            yield rx.toast.warning("Model is required", position="bottom-right")
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
                        "model": self.new_limit_model.strip(),
                        "type": limit_type,
                        "value": value,
                    })
                except ValueError:
                    yield rx.toast.warning(f"{limit_type.upper()} value must be a number", position="bottom-right")
                    return
            else:
                # Empty value means unlimited (None)
                limits_to_add.append({
                    "model": self.new_limit_model.strip(),
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

            # Remove existing limits for this model, then add new ones
            new_limits = [
                {"model": lim.model, "type": lim.type, "value": lim.value} for lim in role.limits if lim.model != self.new_limit_model.strip()
            ]
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
                    self.new_limit_model = ""
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
    async def delete_model_limits(self, role_id: int, model: str):
        """Delete all limits for a specific model from a role."""
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

            # Remove all limits for this model
            new_limits = [{"model": lim.model, "type": lim.type, "value": lim.value} for lim in role.limits if lim.model != model]

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
    async def prev_roles_page(self):
        """Go to previous page of roles."""
        if self.roles_page > 1:
            self.roles_page -= 1
            yield
            async for _ in self.load_roles():
                yield

    @rx.event
    async def next_roles_page(self):
        """Go to next page of roles."""
        if self.has_more_roles:
            self.roles_page += 1
            yield
            async for _ in self.load_roles():
                yield
