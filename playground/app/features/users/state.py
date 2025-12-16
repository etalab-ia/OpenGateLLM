import datetime as dt

import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.users.models import User
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState


class UsersState(EntityState):
    """Users management state."""

    @rx.var
    def roles_name_list(self) -> list[str]:
        return sorted([role["name"] for role in self.roles_list])

    @rx.var
    def organizations_name_list(self) -> list[str]:
        return sorted([organization["name"] for organization in self.organizations_list])

    ############################################################
    # Load entities
    ############################################################
    entities: list[User] = []
    roles_list: list[dict[str, str | int]] = []
    roles_dict: dict[str, int] = {}
    organizations_list: list[dict[str, str | int]] = []
    organizations_dict: dict[str, int] = {}

    def _format_user(self, user: dict) -> User:
        """Format user."""

        organization_dict_reverse = {v: k for k, v in self.organizations_dict.items()}
        role_dict_reverse = {v: k for k, v in self.roles_dict.items()}

        role_name = role_dict_reverse[user["role"]]
        organization_name = organization_dict_reverse.get(user["organization"], None)

        return User(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=role_name,
            organization=organization_name,
            budget=user["budget"],
            priority=user["priority"],
            expires=dt.datetime.fromtimestamp(user["expires"]).strftime("%Y-%m-%d %H:%M") if user["expires"] else None,
            created=dt.datetime.fromtimestamp(user["created"]).strftime("%Y-%m-%d %H:%M"),
            updated=dt.datetime.fromtimestamp(user["updated"]).strftime("%Y-%m-%d %H:%M"),
        )

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
            "order_by": self.order_by_value,
            "order_direction": self.order_direction_value,
        }

        if self.filter_role_value != "0":
            params["role"] = int(self.filter_role_value)
        if self.filter_organization_value != "0":
            params["organization"] = int(self.filter_organization_value)
        if self.search_email_value:
            params["email"] = self.search_email_value

        response = None
        try:
            async with httpx.AsyncClient() as client:
                # Load roles
                if not self.roles_list:
                    offset = 0
                    self.roles_list = []
                    self.roles_dict = {}
                    while True:
                        response = await client.get(
                            url=f"{self.opengatellm_url}/v1/admin/roles",
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            timeout=configuration.settings.playground_opengatellm_timeout,
                        )

                        response.raise_for_status()
                        data = response.json()
                        roles_data = data.get("data", [])
                        self.roles_list.extend([{"id": role["id"], "name": role["name"]} for role in roles_data])
                        self.roles_dict.update({role["name"]: role["id"] for role in roles_data})
                        offset += 100
                        if len(roles_data) < 100:
                            break

                # Load organizations
                if not self.organizations_list:
                    offset = 0
                    self.organizations_list = []
                    self.organizations_dict = {}
                    while True:
                        response = await client.get(
                            url=f"{self.opengatellm_url}/v1/admin/organizations",
                            params={"offset": offset, "limit": 100},
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            timeout=configuration.settings.playground_opengatellm_timeout,
                        )

                        response.raise_for_status()
                        data = response.json()
                        organizations_data = data.get("data", [])
                        self.organizations_list.extend([{"id": org["id"], "name": org["name"]} for org in organizations_data])
                        self.organizations_dict.update({org["name"]: org["id"] for org in organizations_data})
                        offset += 100
                        if len(organizations_data) < 100:
                            break

                # Load users
                response = await client.get(
                    url=f"{self.opengatellm_url}/v1/admin/users",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )

                response.raise_for_status()
                data = response.json()
                self.entities = []
                for user in data.get("data", []):
                    self.entities.append(self._format_user(user))

            self.has_more_page = len(self.entities) == self.per_page

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.entities_loading = False
            yield

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
                    timeout=configuration.settings.playground_opengatellm_timeout,
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

        self.create_entity_loading = True
        yield

        for role in self.roles_list:
            if role["name"] == self.entity_to_create.role:
                role_id = role["id"]
                break
        else:
            yield rx.toast.warning("Role not found", position="bottom-right")
            return

        organization_id = None
        for organization in self.organizations_list:
            if organization["name"] == self.entity_to_create.organization:
                organization_id = organization["id"]
                break

        payload = {
            "email": self.entity_to_create.email,
            "password": self.entity_to_create.password,
            "role": role_id,
            "budget": self.entity_to_create.budget,
            "expires": self.entity_to_create.expires,
            "priority": self.entity_to_create.priority,
        }
        if organization_id:
            payload["organization"] = organization_id

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/admin/users",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
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
    def set_entity_settings(self, entity: User):
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
            self.entity = User()

    @rx.event
    async def edit_entity(self):
        """Update a role."""
        self.edit_entity_loading = True
        yield

        role_id = self.roles_dict[self.entity.role]
        organization_id = self.organizations_dict.get(self.entity.organization)

        payload = {
            "email": self.entity.email,
            "name": self.entity.name,
            "role": role_id,
            "budget": self.entity.budget,
            "expires": self.entity.expires,
            "priority": self.entity.priority,
        }
        if self.entity.password:
            payload["password"] = self.entity.password
        if organization_id:
            payload["organization"] = organization_id

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/admin/users/{self.entity.id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
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
    per_page: int = 20
    order_by_options: list[str] = ["id", "name", "created", "updated"]
    search_email_value: str | None = None

    @rx.event
    async def set_search_email(self, value: str):
        self.search_email_value = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_entities():
            yield

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

    filter_role_value: str = "0"
    filter_organization_value: str = "0"

    @rx.event
    async def set_filter_role(self, value: str):
        self.filter_role_value = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_entities():
            yield

    @rx.event
    async def set_filter_organization(self, value: str):
        self.filter_organization_value = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_entities():
            yield
