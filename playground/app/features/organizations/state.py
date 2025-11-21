"""Organizations state management."""

import datetime

import httpx
import reflex as rx

from app.features.chat.state import ChatState
from app.features.organizations.models import FormattedOrganization, Organization


class OrganizationsState(ChatState):
    """State for managing organizations."""

    # Organizations list
    organizations: list[Organization] = []
    organizations_loading: bool = False

    # Pagination
    page: int = 1
    per_page: int = 20
    has_more_page: bool = False
    order_by: str = "id"
    order_direction: str = "asc"

    # Create organization form
    new_organization_name: str = ""
    create_organization_loading: bool = False

    # Delete organization
    organization_to_delete: int | None = None
    delete_organization_loading: bool = False

    # Edit organization
    organization_to_edit: int | None = None
    edit_organization_name: str = ""
    edit_organization_loading: bool = False

    @rx.var
    def organizations_with_formatted_dates(self) -> list[FormattedOrganization]:
        """Get organizations with formatted dates."""
        formatted = []
        for org in self.organizations:
            formatted.append(
                FormattedOrganization(
                    id=org.id,
                    name=org.name,
                    users=org.users,
                    created=datetime.datetime.fromtimestamp(org.created).strftime("%Y-%m-%d %H:%M"),
                    updated=datetime.datetime.fromtimestamp(org.updated).strftime("%Y-%m-%d %H:%M"),
                )
            )
        return formatted

    @rx.var
    def is_delete_organization_dialog_open(self) -> bool:
        """Check if delete organization dialog should be open."""
        return self.organization_to_delete is not None

    @rx.var
    def is_edit_organization_dialog_open(self) -> bool:
        """Check if edit organization dialog should be open."""
        return self.organization_to_edit is not None

    @rx.event
    def previous_organizations_page(self):
        """Go to previous page."""
        if self.has_previous_organizations_page:
            self.organizations_page -= 1

    @rx.event
    def next_organizations_page(self):
        """Go to next page."""
        if self.has_next_organizations_page:
            self.organizations_page += 1

    @rx.event
    async def set_order_by(self, value: str):
        """Set order by field."""
        self.order_by = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_organizations():
            pass

    @rx.event
    async def set_order_direction(self, value: str):
        """Set order direction."""
        self.order_direction = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_organizations():
            pass

    @rx.event
    def set_new_organization_name(self, value: str):
        """Set new organization name."""
        self.new_organization_name = value

    @rx.event
    def set_organization_to_delete(self, organization_id: int | None):
        """Set organization to delete."""
        self.organization_to_delete = organization_id

    @rx.event
    def set_organization_to_edit(self, organization_id: int | None):
        """Set organization to edit and load its data."""
        if organization_id is None:
            self.organization_to_edit = None
            self.edit_organization_name = ""
        else:
            self.organization_to_edit = organization_id
            # Find organization and populate edit form
            for org in self.organizations:
                if org.id == organization_id:
                    self.edit_organization_name = org.name
                    break

    @rx.event
    def set_edit_organization_name(self, value: str):
        """Set edit organization name."""
        self.edit_organization_name = value

    @rx.event
    async def load_organizations(self):
        """Load organizations from API."""
        if not self.is_admin:
            return

        self.organizations_loading = True
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
                    f"{self.opengatellm_url}/v1/admin/organizations",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                items = data.get("data", [])
                self.organizations = [Organization(**item) for item in items]

                self.has_more_page = len(items) == self.per_page

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
            self.organizations = []
        finally:
            self.organizations_loading = False
            yield

    @rx.event
    async def create_organization(self):
        """Create a new organization."""
        if not self.new_organization_name.strip():
            yield rx.toast.warning("Organization name is required", position="bottom-right")
            return

        self.create_organization_loading = True
        yield

        try:
            payload = {"name": self.new_organization_name.strip()}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.opengatellm_url}/v1/admin/organizations",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=60.0,
                )
                response.raise_for_status()

                if response.status_code == 201:
                    self.new_organization_name = ""
                    yield rx.toast.success("Organization created successfully", position="bottom-right")
                    # Reload organizations
                    async for _ in self.load_organizations():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to create organization")
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
            self.create_organization_loading = False
            yield

    @rx.event
    async def delete_organization(self, organization_id: int):
        """Delete an organization."""
        self.delete_organization_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.opengatellm_url}/v1/admin/organizations/{organization_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    self.organization_to_delete = None
                    yield rx.toast.success("Organization deleted successfully", position="bottom-right")
                    # Reload organizations
                    async for _ in self.load_organizations():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to delete organization")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.delete_organization_loading = False
            yield

    @rx.event
    async def update_organization(self):
        """Update an organization name."""
        if self.organization_to_edit is None:
            return

        if not self.edit_organization_name.strip():
            yield rx.toast.warning("Organization name is required", position="bottom-right")
            return

        self.edit_organization_loading = True
        yield

        try:
            payload = {
                "name": self.edit_organization_name.strip(),
            }

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.opengatellm_url}/v1/admin/organizations/{self.organization_to_edit}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    self.organization_to_edit = None
                    yield rx.toast.success("Organization updated successfully", position="bottom-right")
                    # Reload organizations
                    async for _ in self.load_organizations():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to update organization")
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
            self.edit_organization_loading = False
            yield

    @rx.event
    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            yield
            async for _ in self.load_organizations():
                yield

    @rx.event
    async def next_page(self):
        if self.has_more_page:
            self.page += 1
            yield
            async for _ in self.load_organizations():
                yield
