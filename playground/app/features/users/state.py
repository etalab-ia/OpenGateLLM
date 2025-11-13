import datetime

import httpx
import reflex as rx

from app.features.chat.state import ChatState
from app.features.users.models import FormattedUser, User


class UsersState(ChatState):
    """State for users management."""

    # Users list
    users: list[User] = []
    users_loading: bool = False

    # Pagination for users
    users_page: int = 1
    users_limit: int = 10
    users_total: int = 0
    users_order_by: str = "id"
    users_order_direction: str = "asc"

    # Filters
    filter_role: int | None = None
    filter_organization: int | None = None
    filter_role_value: str = "all"  # Display value for select
    filter_organization_value: str = "all"  # Display value for select

    # Create user form
    new_user_email: str = ""
    new_user_name: str = ""
    new_user_password: str = ""
    new_user_role: str = ""
    new_user_organization: str = ""
    new_user_budget: str = ""
    new_user_expires: str = ""
    new_user_priority: str = "0"
    create_user_loading: bool = False

    # Delete user
    user_to_delete: int | None = None
    delete_user_loading: bool = False

    # Edit user
    user_to_edit: int | None = None
    edit_user_email: str = ""
    edit_user_name: str = ""
    edit_user_password: str = ""
    edit_user_role: str = ""
    edit_user_organization: str = ""
    edit_user_budget: str = ""
    edit_user_expires: str = ""
    edit_user_priority: str = ""
    edit_user_loading: bool = False

    # Available roles and organizations (to be loaded from API)
    available_roles: list[dict] = []
    available_organizations: list[dict] = []

    @rx.var
    def roles_map(self) -> dict[int, str]:
        """Map role IDs to names."""
        return {role["id"]: role["name"] for role in self.available_roles}

    @rx.var
    def organizations_map(self) -> dict[int, str]:
        """Map organization IDs to names."""
        return {org["id"]: org["name"] for org in self.available_organizations}

    @rx.var
    def users_with_formatted_dates(self) -> list[FormattedUser]:
        """Get users with formatted dates."""
        formatted = []
        for user in self.users:
            expires_formatted = None
            if user.expires:
                expires_formatted = datetime.datetime.fromtimestamp(user.expires).strftime("%Y-%m-%d %H:%M")

            # Get role and organization names
            role_name = self.roles_map.get(user.role, f"Role {user.role}")
            organization_name = None
            if user.organization is not None:
                organization_name = self.organizations_map.get(user.organization, f"Org {user.organization}")

            formatted.append(
                FormattedUser(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                    sub=user.sub,
                    iss=user.iss,
                    role=user.role,
                    role_name=role_name,
                    organization=user.organization,
                    organization_name=organization_name,
                    budget=user.budget,
                    expires=user.expires,
                    created=datetime.datetime.fromtimestamp(user.created).strftime("%Y-%m-%d %H:%M"),
                    updated=datetime.datetime.fromtimestamp(user.updated).strftime("%Y-%m-%d %H:%M"),
                    priority=user.priority,
                    expires_formatted=expires_formatted,
                )
            )
        return formatted

    @rx.var
    def users_total_pages(self) -> int:
        """Calculate total pages for users."""
        if self.users_total == 0:
            return 0
        return (self.users_total + self.users_limit - 1) // self.users_limit

    @rx.var
    def has_more_users(self) -> bool:
        """Check if there are more users to load."""
        return self.users_page < self.users_total_pages

    @rx.var
    def is_delete_user_dialog_open(self) -> bool:
        """Check if delete user dialog should be open."""
        return self.user_to_delete is not None

    @rx.var
    def is_edit_user_dialog_open(self) -> bool:
        """Check if edit user dialog should be open."""
        return self.user_to_edit is not None

    @rx.var
    def roles_list_for_dropdown(self) -> list[str]:
        """Get list of role IDs formatted for dropdown."""
        return [str(role["id"]) for role in self.available_roles]

    @rx.var
    def organizations_list_for_dropdown(self) -> list[dict[str, str]]:
        """Get list of organization IDs formatted for dropdown."""
        return [{"id": "None", "name": "Without organization"}] + self.available_organizations

    # Event handlers
    @rx.event
    async def set_users_order_by(self, value: str):
        """Set order by field and reload."""
        self.users_order_by = value
        self.users_page = 1
        yield
        async for _ in self.load_users():
            yield

    @rx.event
    async def set_users_order_direction(self, value: str):
        """Set order direction and reload."""
        self.users_order_direction = value
        self.users_page = 1
        yield
        async for _ in self.load_users():
            yield

    @rx.event
    async def set_filter_role(self, value: str):
        """Set role filter and reload."""
        self.filter_role_value = value
        self.filter_role = int(value) if value and value != "all" else None
        self.users_page = 1
        yield
        async for _ in self.load_users():
            yield

    @rx.event
    async def set_filter_organization(self, value: str):
        """Set organization filter and reload."""
        self.filter_organization_value = value
        if value == "none":
            self.filter_organization = None  # Special value for "without organization"
        elif value and value != "all":
            self.filter_organization = int(value)
        else:
            self.filter_organization = None
        self.users_page = 1
        yield
        async for _ in self.load_users():
            yield

    @rx.event
    def set_new_user_email(self, value: str):
        """Set new user email."""
        self.new_user_email = value

    @rx.event
    def set_new_user_name(self, value: str):
        """Set new user name."""
        self.new_user_name = value

    @rx.event
    def set_new_user_password(self, value: str):
        """Set new user password."""
        self.new_user_password = value

    @rx.event
    def set_new_user_role(self, value: str):
        """Set new user role."""
        self.new_user_role = value

    @rx.event
    def set_new_user_organization(self, value: str):
        """Set new user organization."""
        self.new_user_organization = value

    @rx.event
    def set_new_user_budget(self, value: str):
        """Set new user budget."""
        self.new_user_budget = value

    @rx.event
    def set_new_user_expires(self, value: str):
        """Set new user expires."""
        self.new_user_expires = value

    @rx.event
    def set_new_user_priority(self, value: str):
        """Set new user priority."""
        self.new_user_priority = value

    @rx.event
    def set_user_to_delete(self, user_id: int | None):
        """Set user to delete."""
        self.user_to_delete = user_id

    @rx.event
    def set_user_to_edit(self, user_id: int | None):
        """Set user to edit and load their data."""
        if user_id is None:
            self.user_to_edit = None
            self.edit_user_email = ""
            self.edit_user_name = ""
            self.edit_user_password = ""
            self.edit_user_role = ""
            self.edit_user_organization = ""
            self.edit_user_budget = ""
            self.edit_user_expires = ""
            self.edit_user_priority = ""
        else:
            self.user_to_edit = user_id
            # Find user and populate edit form
            for user in self.users:
                if user.id == user_id:
                    self.edit_user_email = user.email
                    self.edit_user_name = user.name or ""
                    self.edit_user_password = ""
                    self.edit_user_role = str(user.role)
                    self.edit_user_organization = str(user.organization) if user.organization else ""
                    self.edit_user_budget = str(user.budget) if user.budget is not None else ""
                    # Convert timestamp to date format (YYYY-MM-DD)
                    if user.expires:
                        self.edit_user_expires = datetime.datetime.fromtimestamp(user.expires).strftime("%Y-%m-%d")
                    else:
                        self.edit_user_expires = ""
                    self.edit_user_priority = str(user.priority)
                    break

    @rx.event
    def set_edit_user_email(self, value: str):
        """Set edit user email."""
        self.edit_user_email = value

    @rx.event
    def set_edit_user_name(self, value: str):
        """Set edit user name."""
        self.edit_user_name = value

    @rx.event
    def set_edit_user_password(self, value: str):
        """Set edit user password."""
        self.edit_user_password = value

    @rx.event
    def set_edit_user_role(self, value: str):
        """Set edit user role."""
        self.edit_user_role = value

    @rx.event
    def set_edit_user_organization(self, value: str):
        """Set edit user organization."""
        self.edit_user_organization = value

    @rx.event
    def set_edit_user_budget(self, value: str):
        """Set edit user budget."""
        self.edit_user_budget = value

    @rx.event
    def set_edit_user_expires(self, value: str):
        """Set edit user expires."""
        self.edit_user_expires = value

    @rx.event
    def set_edit_user_priority(self, value: str):
        """Set edit user priority."""
        self.edit_user_priority = value

    @rx.event
    async def load_users(self):
        """Load users from API."""
        if not self.is_authenticated or not self.api_key:
            return

        self.users_loading = True
        yield

        try:
            params = {
                "offset": (self.users_page - 1) * self.users_limit,
                "limit": self.users_limit,
                "order_by": self.users_order_by,
                "order_direction": self.users_order_direction,
            }

            if self.filter_role is not None:
                params["role"] = self.filter_role

            if self.filter_organization is not None:
                params["organization"] = self.filter_organization

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/users",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code != 200:
                    error_detail = response.json().get("detail", "Failed to load users")
                    yield rx.toast.error(str(error_detail), position="bottom-right")
                else:
                    data = response.json()
                    users_data = data.get("data", [])
                    self.users = [User(**u) for u in users_data]
                    # Estimate total (API doesn't return total, so we estimate)
                    if len(self.users) < self.users_limit:
                        self.users_total = (self.users_page - 1) * self.users_limit + len(self.users)
                    else:
                        self.users_total = self.users_page * self.users_limit + 1

        except Exception as e:
            yield rx.toast.error(f"Error loading users: {str(e)}", position="bottom-right")
        finally:
            self.users_loading = False
            yield

    @rx.event
    async def load_roles(self):
        """Load available roles from API."""
        if not self.is_authenticated or not self.api_key:
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/roles",
                    params={"offset": 0, "limit": 100},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    roles_data = data.get("data", [])
                    self.available_roles = [{"id": r["id"], "name": r["name"]} for r in roles_data]

        except Exception as e:
            yield rx.toast.error(f"Error loading roles: {str(e)}", position="bottom-right")

    @rx.event
    async def load_organizations(self):
        """Load available organizations from API."""
        if not self.is_authenticated or not self.api_key:
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/organizations",
                    params={"offset": 0, "limit": 100},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    orgs_data = data.get("data", [])
                    self.available_organizations = [{"id": o["id"], "name": o["name"]} for o in orgs_data]

        except Exception as e:
            yield rx.toast.error(f"Error loading organizations: {str(e)}", position="bottom-right")

    @rx.event
    async def create_user(self):
        """Create a new user."""
        if not self.new_user_email.strip():
            yield rx.toast.warning("Email is required", position="bottom-right")
            return

        if not self.new_user_password.strip():
            yield rx.toast.warning("Password is required", position="bottom-right")
            return

        if not self.new_user_role:
            yield rx.toast.warning("Role is required", position="bottom-right")
            return

        self.create_user_loading = True
        yield

        try:
            payload = {
                "email": self.new_user_email.strip(),
                "password": self.new_user_password,
                "role": int(self.new_user_role),
            }

            if self.new_user_name.strip():
                payload["name"] = self.new_user_name.strip()

            if self.new_user_organization:
                payload["organization"] = int(self.new_user_organization)

            if self.new_user_budget.strip():
                try:
                    payload["budget"] = float(self.new_user_budget)
                except ValueError:
                    yield rx.toast.warning("Budget must be a number", position="bottom-right")
                    self.create_user_loading = False
                    yield
                    return

            if self.new_user_expires.strip():
                try:
                    # Convert date string (YYYY-MM-DD) to timestamp
                    date_obj = datetime.datetime.strptime(self.new_user_expires.strip(), "%Y-%m-%d")
                    # Set time to end of day (23:59:59)
                    date_obj = date_obj.replace(hour=23, minute=59, second=59)
                    expires_timestamp = int(date_obj.timestamp())
                    payload["expires"] = expires_timestamp
                except ValueError:
                    yield rx.toast.warning("Invalid date format", position="bottom-right")
                    self.create_user_loading = False
                    yield
                    return

            if self.new_user_priority.strip():
                try:
                    payload["priority"] = int(self.new_user_priority)
                except ValueError:
                    yield rx.toast.warning("Priority must be a number", position="bottom-right")
                    self.create_user_loading = False
                    yield
                    return

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.opengatellm_url}/v1/admin/users",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=60.0,
                )

                if response.status_code == 201:
                    self.new_user_email = ""
                    self.new_user_name = ""
                    self.new_user_password = ""
                    self.new_user_role = ""
                    self.new_user_organization = ""
                    self.new_user_budget = ""
                    self.new_user_expires = ""
                    self.new_user_priority = "0"
                    yield rx.toast.success("User created successfully", position="bottom-right")
                    # Reload users
                    async for _ in self.load_users():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to create user")
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
            self.create_user_loading = False
            yield

    @rx.event
    async def delete_user(self, user_id: int):
        """Delete a user."""
        self.delete_user_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.opengatellm_url}/v1/admin/users/{user_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    self.user_to_delete = None
                    yield rx.toast.success("User deleted successfully", position="bottom-right")
                    # Reload users
                    async for _ in self.load_users():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to delete user")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.delete_user_loading = False
            yield

    @rx.event
    async def update_user(self):
        """Update a user."""
        if self.user_to_edit is None:
            return

        self.edit_user_loading = True
        yield

        try:
            payload = {}

            if self.edit_user_email.strip():
                payload["email"] = self.edit_user_email.strip()

            if self.edit_user_name.strip():
                payload["name"] = self.edit_user_name.strip()

            if self.edit_user_password.strip():
                payload["password"] = self.edit_user_password

            if self.edit_user_role:
                payload["role"] = int(self.edit_user_role)

            if self.edit_user_organization:
                payload["organization"] = int(self.edit_user_organization)
            else:
                payload["organization"] = None

            if self.edit_user_budget.strip():
                try:
                    payload["budget"] = float(self.edit_user_budget)
                except ValueError:
                    yield rx.toast.warning("Budget must be a number", position="bottom-right")
                    self.edit_user_loading = False
                    yield
                    return
            else:
                payload["budget"] = None

            if self.edit_user_expires.strip():
                try:
                    # Convert date string (YYYY-MM-DD) to timestamp
                    date_obj = datetime.datetime.strptime(self.edit_user_expires.strip(), "%Y-%m-%d")
                    # Set time to end of day (23:59:59)
                    date_obj = date_obj.replace(hour=23, minute=59, second=59)
                    expires_timestamp = int(date_obj.timestamp())
                    payload["expires"] = expires_timestamp
                except ValueError:
                    yield rx.toast.warning("Invalid date format", position="bottom-right")
                    self.edit_user_loading = False
                    yield
                    return
            else:
                payload["expires"] = None

            if self.edit_user_priority.strip():
                try:
                    payload["priority"] = int(self.edit_user_priority)
                except ValueError:
                    yield rx.toast.warning("Priority must be a number", position="bottom-right")
                    self.edit_user_loading = False
                    yield
                    return

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.opengatellm_url}/v1/admin/users/{self.user_to_edit}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    self.user_to_edit = None
                    yield rx.toast.success("User updated successfully", position="bottom-right")
                    # Reload users
                    async for _ in self.load_users():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to update user")
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
            self.edit_user_loading = False
            yield

    @rx.event
    async def prev_users_page(self):
        """Go to previous page of users."""
        if self.users_page > 1:
            self.users_page -= 1
            yield
            async for _ in self.load_users():
                yield

    @rx.event
    async def next_users_page(self):
        """Go to next page of users."""
        if self.has_more_users:
            self.users_page += 1
            yield
            async for _ in self.load_users():
                yield
