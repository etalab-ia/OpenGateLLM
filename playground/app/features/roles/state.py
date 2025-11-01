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

    # Selected role for limits
    limits_selected_role_id: int | None = None
    limits_selected_role_name: str = ""

    # Selected role for permissions
    permissions_selected_role_id: int | None = None
    permissions_selected_role_name: str = ""

    # Limits filters
    limits_filter_model: str = "all"

    # Create role form
    new_role_name: str = ""
    create_role_loading: bool = False

    # Delete role
    role_to_delete: int | None = None
    delete_role_loading: bool = False

    # Edit role
    role_to_edit: int | None = None
    edit_role_name: str = ""
    edit_role_loading: bool = False

    # Add limit form
    new_limit_model: str = ""
    new_limit_type: str = "rpm"
    new_limit_value: str = ""
    add_limit_loading: bool = False

    # Delete limit
    delete_limit_loading: bool = False

    # Add permission
    new_permission: str = ""
    add_permission_loading: bool = False

    # Delete permission
    delete_permission_loading: bool = False

    # Available permissions (from schema)
    available_permissions: list[str] = ["admin", "create_public_collection", "read_metric", "provide_models"]

    # Available limit types
    available_limit_types: list[str] = ["rpm", "rpd", "tpm", "tpd"]

    @rx.var
    def is_admin(self) -> bool:
        """Check if user has admin permission."""
        return "admin" in self.user_permissions

    @rx.var
    def roles_with_formatted_dates(self) -> list[FormattedRole]:
        """Get roles with formatted dates."""
        formatted = []
        for role in self.roles:
            formatted.append(
                FormattedRole(
                    id=role.id,
                    name=role.name,
                    permissions=role.permissions,
                    limits=role.limits,
                    users=role.users,
                    created_at=datetime.datetime.fromtimestamp(role.created_at).strftime("%Y-%m-%d %H:%M"),
                    updated_at=datetime.datetime.fromtimestamp(role.updated_at).strftime("%Y-%m-%d %H:%M"),
                )
            )
        return formatted

    @rx.var
    def limits_selected_role(self) -> Role | None:
        """Get the selected role for limits."""
        if self.limits_selected_role_id is None:
            return None
        for role in self.roles:
            if role.id == self.limits_selected_role_id:
                return role
        return None

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
    def selected_role_limits(self) -> list[Limit]:
        """Get limits for selected role."""
        role = self.limits_selected_role
        if role is None:
            return []
        return role.limits

    @rx.var
    def filtered_limits(self) -> list[Limit]:
        """Get filtered limits for selected role."""
        limits = self.selected_role_limits
        if self.limits_filter_model == "all":
            return limits
        return [limit for limit in limits if limit.model == self.limits_filter_model]

    @rx.var
    def limits_models_list(self) -> list[str]:
        """Get list of unique models from selected role limits."""
        role = self.limits_selected_role
        if role is None:
            return []
        models_set = set()
        for limit in role.limits:
            models_set.add(limit.model)
        models_list = []
        for model in models_set:
            models_list.append(model)
        models_list.sort()
        return models_list

    @rx.var
    def limits_models_list_with_all(self) -> list[str]:
        """Get list of models with 'all' option prepended."""
        models = self.limits_models_list
        result = ["all"]
        result.extend(models)
        return result

    @rx.var
    def selected_role_permissions(self) -> list[str]:
        """Get permissions for selected role."""
        role = self.permissions_selected_role
        if role is None:
            return []
        return role.permissions

    @rx.var
    def available_permissions_to_add(self) -> list[str]:
        """Get permissions that can be added to selected role."""
        current_perms = self.selected_role_permissions
        return [p for p in self.available_permissions if p not in current_perms]

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
    def has_limits_selected_role(self) -> bool:
        """Check if a role is selected for limits."""
        return self.limits_selected_role_id is not None

    @rx.var
    def has_permissions_selected_role(self) -> bool:
        """Check if a role is selected for permissions."""
        return self.permissions_selected_role_id is not None

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
    def set_limits_selected_role(self, value: str):
        """Set selected role for limits."""
        if value:
            role_id = int(value)
            for role in self.roles:
                if role.id == role_id:
                    self.limits_selected_role_id = role_id
                    self.limits_selected_role_name = role.name
                    self.limits_filter_model = "all"
                    break
        else:
            self.limits_selected_role_id = None
            self.limits_selected_role_name = ""

    @rx.event
    def set_permissions_selected_role(self, value: str):
        """Set selected role for permissions."""
        if value:
            role_id = int(value)
            for role in self.roles:
                if role.id == role_id:
                    self.permissions_selected_role_id = role_id
                    self.permissions_selected_role_name = role.name
                    break
        else:
            self.permissions_selected_role_id = None
            self.permissions_selected_role_name = ""

    @rx.event
    def set_limits_filter_model(self, value: str):
        """Set limits filter model."""
        self.limits_filter_model = value

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
        else:
            self.role_to_edit = role_id
            # Find role and populate edit form
            for role in self.roles:
                if role.id == role_id:
                    self.edit_role_name = role.name
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
    def set_new_limit_type(self, value: str):
        """Set new limit type."""
        self.new_limit_type = value

    @rx.event
    def set_new_limit_value(self, value: str):
        """Set new limit value."""
        self.new_limit_value = value

    @rx.event
    def set_new_permission(self, value: str):
        """Set new permission."""
        self.new_permission = value

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
                    f"{self.api_url}/v1/admin/roles",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0,
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
                            created_at=r["created_at"],
                            updated_at=r["updated_at"],
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
                "permissions": [],
                "limits": [],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/v1/admin/roles",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=10.0,
                )

                if response.status_code == 201:
                    self.new_role_name = ""
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
                    f"{self.api_url}/v1/admin/roles/{role_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0,
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
        """Update a role name."""
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
            }

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.api_url}/v1/admin/roles/{self.role_to_edit}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=10.0,
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
    async def add_limit(self):
        """Add a limit to selected role."""
        if self.limits_selected_role_id is None:
            yield rx.toast.warning("No role selected", position="bottom-right")
            return

        if not self.new_limit_model.strip():
            yield rx.toast.warning("Model is required", position="bottom-right")
            return

        try:
            value = int(self.new_limit_value) if self.new_limit_value.strip() else None
            if value is not None and value < 0:
                yield rx.toast.warning("Value must be >= 0", position="bottom-right")
                return
        except ValueError:
            yield rx.toast.warning("Value must be a number", position="bottom-right")
            return

        self.add_limit_loading = True
        yield

        try:
            # Get current role limits
            role = self.limits_selected_role
            if role is None:
                yield rx.toast.error("Role not found", position="bottom-right")
                self.add_limit_loading = False
                yield
                return

            # Add new limit
            new_limits = [{"model": lim.model, "type": lim.type, "value": lim.value} for lim in role.limits]
            new_limits.append({
                "model": self.new_limit_model.strip(),
                "type": self.new_limit_type,
                "value": int(self.new_limit_value) if self.new_limit_value.strip() else None,
            })

            payload = {"limits": new_limits}

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.api_url}/v1/admin/roles/{self.limits_selected_role_id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=10.0,
                )

                if response.status_code == 204:
                    self.new_limit_model = ""
                    self.new_limit_type = "rpm"
                    self.new_limit_value = ""
                    yield rx.toast.success("Limit added successfully", position="bottom-right")
                    # Reload roles
                    async for _ in self.load_roles():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to add limit")
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
    async def delete_limit(self, model: str, limit_type: str):
        """Delete a limit from selected role."""
        if self.limits_selected_role_id is None:
            return

        self.delete_limit_loading = True
        yield

        try:
            role = self.limits_selected_role
            if role is None:
                yield rx.toast.error("Role not found", position="bottom-right")
                self.delete_limit_loading = False
                yield
                return

            # Remove the limit
            new_limits = [
                {"model": lim.model, "type": lim.type, "value": lim.value}
                for lim in role.limits
                if not (lim.model == model and lim.type == limit_type)
            ]

            payload = {"limits": new_limits}

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.api_url}/v1/admin/roles/{self.limits_selected_role_id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=10.0,
                )

                if response.status_code == 204:
                    yield rx.toast.success("Limit deleted successfully", position="bottom-right")
                    # Reload roles
                    async for _ in self.load_roles():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to delete limit")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.delete_limit_loading = False
            yield

    @rx.event
    async def add_permission(self):
        """Add a permission to selected role."""
        if self.permissions_selected_role_id is None:
            yield rx.toast.warning("No role selected", position="bottom-right")
            return

        if not self.new_permission:
            yield rx.toast.warning("Permission is required", position="bottom-right")
            return

        self.add_permission_loading = True
        yield

        try:
            role = self.permissions_selected_role
            if role is None:
                yield rx.toast.error("Role not found", position="bottom-right")
                self.add_permission_loading = False
                yield
                return

            # Add new permission
            new_permissions = list(role.permissions)
            if self.new_permission not in new_permissions:
                new_permissions.append(self.new_permission)

            payload = {"permissions": new_permissions}

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.api_url}/v1/admin/roles/{self.permissions_selected_role_id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=10.0,
                )

                if response.status_code == 204:
                    self.new_permission = ""
                    yield rx.toast.success("Permission added successfully", position="bottom-right")
                    # Reload roles
                    async for _ in self.load_roles():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to add permission")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.add_permission_loading = False
            yield

    @rx.event
    async def delete_permission(self, permission: str):
        """Delete a permission from selected role."""
        if self.permissions_selected_role_id is None:
            return

        self.delete_permission_loading = True
        yield

        try:
            role = self.permissions_selected_role
            if role is None:
                yield rx.toast.error("Role not found", position="bottom-right")
                self.delete_permission_loading = False
                yield
                return

            # Remove the permission
            new_permissions = [p for p in role.permissions if p != permission]

            payload = {"permissions": new_permissions}

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.api_url}/v1/admin/roles/{self.permissions_selected_role_id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=10.0,
                )

                if response.status_code == 204:
                    yield rx.toast.success("Permission deleted successfully", position="bottom-right")
                    # Reload roles
                    async for _ in self.load_roles():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to delete permission")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.delete_permission_loading = False
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
