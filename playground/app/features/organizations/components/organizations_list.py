"""Organizations list component with sorting and pagination."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    ICON_SIZE_EMPTY_STATE,
    ICON_SIZE_MEDIUM,
    MARGIN_MEDIUM,
    MAX_DIALOG_WIDTH,
    PADDING_PAGE,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_NONE,
    SPACING_SMALL,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_LARGE,
)
from app.features.organizations.components.organizations_pagination import organizations_pagination
from app.features.organizations.models import FormattedOrganization
from app.features.organizations.state import OrganizationsState


def organization_item(org: FormattedOrganization) -> rx.Component:
    """Display a single organization item."""
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        org.name,
                        size=TEXT_SIZE_LARGE,
                        weight="bold",
                        color=rx.color("mauve", 12),
                    ),
                    rx.badge(
                        org.id.to(str),
                        variant="soft",
                        color_scheme="blue",
                    ),
                    spacing=SPACING_SMALL,
                ),
                rx.hstack(
                    rx.text(
                        f"Created: {org.created}",
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 9),
                    ),
                    rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                    rx.text(
                        f"Updated: {org.updated}",
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 9),
                    ),
                    spacing=SPACING_SMALL,
                ),
                spacing=SPACING_SMALL,
                align_items="start",
                flex="1",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("pencil", size=ICON_SIZE_MEDIUM),
                    on_click=lambda: OrganizationsState.set_organization_to_edit(org.id),
                    variant="soft",
                    color_scheme="blue",
                    size=TEXT_SIZE_LABEL,
                ),
                rx.button(
                    rx.icon("trash-2", size=ICON_SIZE_MEDIUM),
                    on_click=lambda: OrganizationsState.set_organization_to_delete(org.id),
                    variant="soft",
                    color_scheme="red",
                    size=TEXT_SIZE_LABEL,
                ),
                spacing=SPACING_SMALL,
            ),
            width="100%",
            align="center",
            justify="between",
            padding_y="0.75em",
        ),
        rx.divider(),
        width="100%",
    )


def create_organization_form() -> rx.Component:
    """Form to create a new organization."""
    return rx.card(
        rx.vstack(
            rx.heading("Create new organization", size=TEXT_SIZE_LARGE),
            rx.input(
                placeholder="Organization name",
                value=OrganizationsState.new_organization_name,
                on_change=OrganizationsState.set_new_organization_name,
                disabled=OrganizationsState.create_organization_loading,
                width="100%",
            ),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(
                        OrganizationsState.create_organization_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Create",
                    ),
                    on_click=OrganizationsState.create_organization,
                    disabled=OrganizationsState.create_organization_loading,
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )


def edit_organization_dialog() -> rx.Component:
    """Dialog for editing an organization."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Edit Organization"),
            rx.dialog.description(
                "Update the organization name.",
            ),
            rx.vstack(
                rx.text("Organization name *", size=TEXT_SIZE_LABEL, weight="bold"),
                rx.input(
                    placeholder="Organization name",
                    value=OrganizationsState.edit_organization_name,
                    on_change=OrganizationsState.set_edit_organization_name,
                    disabled=OrganizationsState.edit_organization_loading,
                    width="100%",
                ),
                spacing=SPACING_TINY,
                width="100%",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=lambda: OrganizationsState.set_organization_to_edit(None),
                    ),
                ),
                rx.button(
                    rx.cond(
                        OrganizationsState.edit_organization_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Update",
                    ),
                    on_click=OrganizationsState.update_organization,
                    disabled=OrganizationsState.edit_organization_loading,
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
                margin_top=MARGIN_MEDIUM,
            ),
            max_width=MAX_DIALOG_WIDTH,
        ),
        open=OrganizationsState.is_edit_organization_dialog_open,
    )


def delete_organization_dialog() -> rx.Component:
    """Dialog for deleting an organization."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Organization"),
            rx.alert_dialog.description(
                "Are you sure you want to delete this organization? This action cannot be undone.",
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=lambda: OrganizationsState.set_organization_to_delete(None),
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        rx.cond(
                            OrganizationsState.delete_organization_loading,
                            rx.spinner(size=SIZE_MEDIUM),
                            "Delete",
                        ),
                        on_click=lambda: OrganizationsState.delete_organization(OrganizationsState.organization_to_delete),
                        color_scheme="red",
                        disabled=OrganizationsState.delete_organization_loading,
                    ),
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
            ),
            spacing=SPACING_LARGE,
        ),
        open=OrganizationsState.is_delete_organization_dialog_open,
    )


def organizations_sorting() -> rx.Component:
    """Sorting controls for organizations."""
    return rx.hstack(
        rx.text("Sort by", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select(
            ["id", "name", "created", "updated"],
            value=OrganizationsState.organizations_order_by,
            on_change=OrganizationsState.set_organizations_order_by,
        ),
        rx.select(
            ["asc", "desc"],
            value=OrganizationsState.organizations_order_direction,
            on_change=OrganizationsState.set_organizations_order_direction,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def organizations_list() -> rx.Component:
    """Display list of organizations with sorting and pagination."""
    return rx.vstack(
        create_organization_form(),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading("Organizations", size=HEADING_SIZE_SECTION),
                    rx.badge(
                        OrganizationsState.organizations.length(),
                        variant="soft",
                        color_scheme="blue",
                    ),
                    rx.spacer(),
                    organizations_sorting(),
                    align="center",
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                rx.divider(),
                rx.cond(
                    OrganizationsState.organizations_loading,
                    rx.center(
                        rx.spinner(size=SIZE_MEDIUM),
                        width="100%",
                        padding=PADDING_PAGE,
                    ),
                    rx.cond(
                        OrganizationsState.organizations.length() > 0,
                        rx.vstack(
                            rx.foreach(OrganizationsState.organizations_with_formatted_dates, organization_item),
                            spacing=SPACING_NONE,
                            width="100%",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("building", size=ICON_SIZE_EMPTY_STATE, color=rx.color("mauve", 8)),
                                rx.text(
                                    "No organizations yet",
                                    size=TEXT_SIZE_LARGE,
                                    color=rx.color("mauve", 10),
                                ),
                                rx.text(
                                    "Create your first organization to get started",
                                    size=TEXT_SIZE_LABEL,
                                    color=rx.color("mauve", 9),
                                ),
                                spacing=SPACING_SMALL,
                            ),
                            width="100%",
                            padding=PADDING_PAGE,
                        ),
                    ),
                ),
                rx.cond(
                    OrganizationsState.organizations.length() > 0,
                    rx.hstack(
                        organizations_pagination(),
                        width="100%",
                        justify="end",
                    ),
                ),
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            width="100%",
        ),
        edit_organization_dialog(),
        delete_organization_dialog(),
        spacing=SPACING_LARGE,
        width="100%",
    )
