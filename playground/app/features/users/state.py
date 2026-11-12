import math

import httpx
import reflex as rx

from app.features.users.models import User
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState
from app.shared.utils.timestamps import date_to_timestamp, format_date, format_datetime


class UsersState(EntityState):
    """Users management state."""

    @rx.var
    def roles_name_list(self) -> list[str]:
        return sorted([role["name"] for role in self.roles_list])

    @rx.var
    def organizations_name_list(self) -> list[str]:
        return sorted([organization["name"] for organization in self.organizations_list])

    def _format_user(self, user: dict) -> User:
        """Format user."""
        return User(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role_id=user["role_id"],
            organization_id=user["organization_id"],
            priority=user["priority"],
            expires=format_date(user["expires"]) if user["expires"] else None,
            created=format_datetime(user["created"]),
            updated=format_datetime(user["updated"]),
        )

    ############################################################
    # Load entities
    ############################################################
    entities: list[User] = []
    roles_list: list[dict[str, str | int]] = []
    roles_dict: dict[str, int] = {}
    organizations_list: list[dict[str, str | int]] = []
    organizations_dict: dict[str, int] = {}

    @rx.var
    def users(self) -> list[User]:
        """Get users list with correct typing for Reflex."""
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
            "sort_by": self.order_by_value,
            "sort_order": self.order_direction_value,
        }

        search_email = self.search_email_value.strip()
        if search_email:
            params["email"] = search_email
        search_role = self.search_role_value.strip()
        if search_role:
            params["role_name"] = search_role
        search_organization = self.search_organization_value.strip()
        if search_organization:
            params["organization_name"] = search_organization

        response = None
        try:
            async with httpx.AsyncClient() as client:
                # Load users
                response = await client.get(
                    url=f"{self.opengatellm_url}/v1/admin/users",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=self.opengatellm_timeout,
                )

                response.raise_for_status()
                data = response.json()
                self.entities = []
                for user in data.get("data", []):
                    self.entities.append(self._format_user(user))

            self.total = data.get("total", 0)

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.entities_loading = False
            yield

    ############################################################
    # Form options (roles and organizations)
    ############################################################
    async def _fetch_all_names(self, client: httpx.AsyncClient, path: str) -> list[dict[str, str | int]]:
        """Fetch every {id, name} of a paginated admin resource."""
        items = []
        offset = 0
        while True:
            response = await client.get(
                url=f"{self.opengatellm_url}{path}",
                params={"offset": offset, "limit": 100},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.opengatellm_timeout,
            )
            response.raise_for_status()
            page = response.json().get("data", [])
            items.extend([{"id": item["id"], "name": item["name"]} for item in page])
            offset += 100
            if len(page) < 100:
                return items

    async def _load_form_options(self):
        """Load the roles and organizations the create and edit forms select from."""
        async with httpx.AsyncClient() as client:
            self.roles_list = await self._fetch_all_names(client, "/v1/admin/roles")
            self.organizations_list = await self._fetch_all_names(client, "/v1/admin/organizations")
        self.roles_dict = {role["name"]: role["id"] for role in self.roles_list}
        self.organizations_dict = {organization["name"]: organization["id"] for organization in self.organizations_list}

    @rx.event
    async def handle_form_select_open_change(self, is_open: bool):
        """Load the form options when a create form select opens."""
        if not is_open:
            return
        try:
            await self._load_form_options()
        except httpx.HTTPStatusError as e:
            yield httpx_error_toast(exception=e, response=e.response)
        except Exception as e:
            yield httpx_error_toast(exception=e)

    ############################################################
    # Delete entity
    ############################################################
    entity_to_delete: User = User()

    @rx.event
    def set_entity_to_delete(self, entity: User):
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
            self.entity_to_delete = User()

    async def delete_entity(self):
        """Delete a user."""
        self.delete_entity_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/admin/users/{self.entity_to_delete.id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=self.opengatellm_timeout,
                )
                response.raise_for_status()

                self.handle_delete_entity_dialog_change(is_open=False)
                yield rx.toast.success("User deleted successfully", position="bottom-right")
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
    entity_to_create: User = User()

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
        if not self.entity_to_create.email:
            yield rx.toast.warning("User email is required", position="bottom-right")
            return

        if not self.entity_to_create.password:
            yield rx.toast.warning("User password is required", position="bottom-right")
            return

        if not self.entity_to_create.role:
            yield rx.toast.warning("Role is required", position="bottom-right")
            return

        if not self.entity_to_create.organization:
            yield rx.toast.warning("Organization is required", position="bottom-right")
            return

        for role in self.roles_list:
            if role["name"] == self.entity_to_create.role:
                role_id = role["id"]
                break
        else:
            yield rx.toast.warning("Role not found", position="bottom-right")
            return

        for organization in self.organizations_list:
            if organization["name"] == self.entity_to_create.organization:
                organization_id = organization["id"]
                break
        else:
            yield rx.toast.warning("Organization not found", position="bottom-right")
            return

        self.create_entity_loading = True

        yield

        payload = {
            "email": self.entity_to_create.email,
            "password": self.entity_to_create.password,
            "role_id": role_id,
            "organization_id": organization_id,
            "priority": self.entity_to_create.priority,
        }

        if self.entity_to_create.expires:
            payload["expires"] = date_to_timestamp(self.entity_to_create.expires)

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/admin/users",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=self.opengatellm_timeout,
                )
                response.raise_for_status()

                yield rx.toast.success("User created successfully", position="bottom-right")
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
    entity: User = User()

    @rx.event
    async def set_entity_settings(self, entity: User):
        """Open the settings dialog, resolving the role and organization names it displays."""
        try:
            await self._load_form_options()
        except httpx.HTTPStatusError as e:
            yield httpx_error_toast(exception=e, response=e.response)
            return
        except Exception as e:
            yield httpx_error_toast(exception=e)
            return

        self.entity = entity
        role_names = {role_id: name for name, role_id in self.roles_dict.items()}
        organization_names = {organization_id: name for name, organization_id in self.organizations_dict.items()}
        self.entity.role = role_names.get(self.entity.role_id)
        self.entity.organization = organization_names.get(self.entity.organization_id)

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
            self.entity = User()

    @rx.event
    async def edit_entity(self):
        """Update a user."""
        self.edit_entity_loading = True
        yield

        payload = {
            "email": self.entity.email,
            "name": self.entity.name or None,
            "role_id": self.roles_dict[self.entity.role],
            "organization_id": self.organizations_dict[self.entity.organization],
            "expires": date_to_timestamp(self.entity.expires) if self.entity.expires else None,
            "priority": self.entity.priority,
        }
        if self.entity.password:
            payload["password"] = self.entity.password

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/admin/users/{self.entity.id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=self.opengatellm_timeout,
                )
            response.raise_for_status()

            self.handle_settings_entity_dialog_change(is_open=False)
            yield rx.toast.success("User updated successfully", position="bottom-right")

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
    total: int = 0
    order_by_value: str = "id"
    order_direction: str = "asc"
    order_direction_options: list[str] = ["asc", "desc"]
    order_direction_value: str = "asc"
    order_by_options: list[str] = ["id", "name", "created", "updated"]
    search_email_value: str = ""

    @rx.var
    def total_pages(self) -> int:
        return max(1, math.ceil(self.total / self.per_page))

    @rx.var
    def has_active_filters(self) -> bool:
        return any(value.strip() for value in (self.search_email_value, self.search_role_value, self.search_organization_value))

    @rx.event
    async def set_search_email(self, value: str):
        self.search_email_value = value
        self.page = 1
        yield
        async for _ in self.load_entities():
            yield

    @rx.event
    async def set_order_by(self, value: str):
        """Set order by field and reload."""
        self.order_by_value = value
        self.page = 1
        yield
        async for _ in self.load_entities():
            yield

    @rx.event
    async def set_order_direction(self, value: str):
        """Set order direction and reload."""
        self.order_direction_value = value
        self.page = 1
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
        if self.page < self.total_pages:
            self.page += 1
            yield
            async for _ in self.load_entities():
                yield

    search_role_value: str = ""
    search_organization_value: str = ""

    @rx.event
    async def set_search_role(self, value: str):
        self.search_role_value = value
        self.page = 1
        yield
        async for _ in self.load_entities():
            yield

    @rx.event
    async def set_search_organization(self, value: str):
        self.search_organization_value = value
        self.page = 1
        yield
        async for _ in self.load_entities():
            yield
