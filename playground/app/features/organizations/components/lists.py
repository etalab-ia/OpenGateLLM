import reflex as rx

from app.core.variables import SELECT_LARGE_WIDTH, SPACING_SMALL, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.organizations.components.dialogs import organization_delete_dialog, organization_settings_dialog
from app.features.organizations.models import Organization
from app.features.organizations.state import OrganizationsState
from app.shared.components.lists import entity_list, entity_row


def organization_row_content(organization: Organization) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                organization.name,
                size=TEXT_SIZE_LARGE,
                weight="bold",
                color=rx.color("mauve", 12),
            ),
            rx.tooltip(
                rx.badge(
                    organization.id.to(str),
                    variant="soft",
                    color_scheme="blue",
                ),
                content="ID",
            ),
            rx.badge(
                organization.users.to(str) + " user" + rx.cond(organization.users != 1, "s", ""),
                variant="soft",
                color_scheme="green",
            ),
            spacing=SPACING_SMALL,
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def organization_row_description(organization: Organization) -> rx.Component:
    return rx.vstack(
        rx.text(
            f"Created: {organization.created} • Updated: {organization.updated}",
            size=TEXT_SIZE_LABEL,
            color=rx.color("mauve", 9),
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def organization_renderer_row(organization: Organization, with_settings: bool = False) -> rx.Component:
    """Display a row with user information."""
    return entity_row(
        state=OrganizationsState,
        entity=organization,
        row_content=organization_row_content(organization),
        row_description=organization_row_description(organization),
        with_settings=with_settings,
    )


def organization_filters() -> rx.Component:
    """Filters for organizations list."""
    return rx.hstack(
        rx.text("Search", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.input(
            type="text",
            value=OrganizationsState.search_name_value,
            on_change=OrganizationsState.set_search_name,
            placeholder="Enter name",
            width=SELECT_LARGE_WIDTH,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def organizations_list() -> rx.Component:
    """Users list."""
    return entity_list(
        state=OrganizationsState,
        title="Organizations",
        entities=OrganizationsState.organizations,
        renderer_entity_row=organization_renderer_row,
        no_entities_message=rx.cond(
            OrganizationsState.has_search_name,
            "No organizations found",
            "No organizations yet",
        ),
        no_entities_description=rx.cond(
            OrganizationsState.has_search_name,
            "No organization name matches your search",
            "Create your first organization to get started",
        ),
        settings_dialog=organization_settings_dialog(),
        delete_dialog=organization_delete_dialog(),
        filters=organization_filters(),
        pagination=True,
        sorting=True,
    )
