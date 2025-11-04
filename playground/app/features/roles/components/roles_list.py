import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    ICON_SIZE_EMPTY_STATE,
    ICON_SIZE_MEDIUM,
    MARGIN_MEDIUM,
    MAX_CARD_WIDTH,
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
from app.features.roles.components.roles_pagination import roles_pagination
from app.features.roles.models import FormattedRole
from app.features.roles.state import RolesState


def role_item(role: FormattedRole) -> rx.Component:
    """Display a single role item."""
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        role.name,
                        size=TEXT_SIZE_LARGE,
                        weight="bold",
                        color=rx.color("mauve", 12),
                    ),
                    rx.badge(
                        role.id.to(str),
                        variant="soft",
                        color_scheme="blue",
                    ),
                    rx.badge(
                        role.users.to(str) + " user" + rx.cond(role.users != 1, "s", ""),
                        variant="soft",
                        color_scheme="green",
                    ),
                    spacing=SPACING_SMALL,
                ),
                rx.hstack(
                    rx.text(
                        f"Created: {role.created_at}",
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 9),
                    ),
                    rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                    rx.text(
                        f"Updated: {role.updated_at}",
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 9),
                    ),
                    spacing=SPACING_SMALL,
                ),
                rx.hstack(
                    rx.text(
                        role.permissions.length().to(str) + " permission" + rx.cond(role.permissions.length() != 1, "s", ""),
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 10),
                    ),
                    rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                    rx.text(
                        role.limits.length().to(str) + " limit" + rx.cond(role.limits.length() != 1, "s", ""),
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 10),
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
                    on_click=lambda: RolesState.set_role_to_edit(role.id),
                    variant="soft",
                    color_scheme="blue",
                    size=TEXT_SIZE_LABEL,
                ),
                rx.button(
                    rx.icon("trash-2", size=ICON_SIZE_MEDIUM),
                    on_click=lambda: RolesState.set_role_to_delete(role.id),
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


def create_role_form() -> rx.Component:
    """Form to create a new role."""
    return rx.card(
        rx.vstack(
            rx.heading("Create new role", size=TEXT_SIZE_LARGE),
            rx.hstack(
                rx.input(
                    placeholder="Role name",
                    value=RolesState.new_role_name,
                    on_change=RolesState.set_new_role_name,
                    disabled=RolesState.create_role_loading,
                    width="100%",
                ),
                rx.button(
                    rx.cond(
                        RolesState.create_role_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Create",
                    ),
                    on_click=RolesState.create_role,
                    disabled=RolesState.create_role_loading,
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )


def edit_role_dialog() -> rx.Component:
    """Dialog for editing a role."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Edit Role"),
            rx.dialog.description(
                "Update the role name.",
            ),
            rx.vstack(
                rx.text("Role Name *", size=TEXT_SIZE_LABEL, weight="bold"),
                rx.input(
                    placeholder="Role name",
                    value=RolesState.edit_role_name,
                    on_change=RolesState.set_edit_role_name,
                    disabled=RolesState.edit_role_loading,
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
                        on_click=lambda: RolesState.set_role_to_edit(None),
                    ),
                ),
                rx.button(
                    rx.cond(
                        RolesState.edit_role_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Update",
                    ),
                    on_click=RolesState.update_role,
                    disabled=RolesState.edit_role_loading,
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
                margin_top=MARGIN_MEDIUM,
            ),
            max_width=MAX_DIALOG_WIDTH,
        ),
        open=RolesState.is_edit_role_dialog_open,
    )


def delete_role_dialog() -> rx.Component:
    """Dialog for deleting a role."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Role"),
            rx.alert_dialog.description(
                "Are you sure you want to delete this role? This action cannot be undone.",
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=lambda: RolesState.set_role_to_delete(None),
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        rx.cond(
                            RolesState.delete_role_loading,
                            rx.spinner(size=SIZE_MEDIUM),
                            "Delete",
                        ),
                        on_click=lambda: RolesState.delete_role(RolesState.role_to_delete),
                        color_scheme="red",
                        disabled=RolesState.delete_role_loading,
                    ),
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
            ),
            spacing=SPACING_LARGE,
        ),
        open=RolesState.is_delete_role_dialog_open,
    )


def roles_sorting() -> rx.Component:
    """Sorting controls for roles."""
    return rx.hstack(
        rx.text("Sort by", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select(
            ["id", "name", "created_at", "updated_at"],
            value=RolesState.roles_order_by,
            on_change=RolesState.set_roles_order_by,
        ),
        rx.select(
            ["asc", "desc"],
            value=RolesState.roles_order_direction,
            on_change=RolesState.set_roles_order_direction,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def roles_list() -> rx.Component:
    """Display list of roles with sorting and pagination."""
    return rx.vstack(
        create_role_form(),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading("Roles", size=HEADING_SIZE_SECTION),
                    rx.badge(
                        RolesState.roles.length(),
                        variant="soft",
                        color_scheme="blue",
                    ),
                    rx.spacer(),
                    roles_sorting(),
                    align="center",
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                rx.divider(),
                rx.cond(
                    RolesState.roles_loading,
                    rx.center(
                        rx.spinner(size=SIZE_MEDIUM),
                        width="100%",
                        padding=PADDING_PAGE,
                    ),
                    rx.cond(
                        RolesState.roles.length() > 0,
                        rx.vstack(
                            rx.foreach(RolesState.roles_with_formatted_dates, role_item),
                            spacing=SPACING_NONE,
                            width="100%",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("shield", size=ICON_SIZE_EMPTY_STATE, color=rx.color("mauve", 8)),
                                rx.text(
                                    "No roles yet",
                                    size=TEXT_SIZE_LARGE,
                                    color=rx.color("mauve", 10),
                                ),
                                rx.text(
                                    "Create your first role to get started",
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
                    RolesState.roles.length() > 0,
                    rx.hstack(
                        roles_pagination(),
                        width="100%",
                        justify="end",
                    ),
                ),
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            width="100%",
        ),
        edit_role_dialog(),
        delete_role_dialog(),
        spacing=SPACING_LARGE,
        width="100%",
        max_width=MAX_CARD_WIDTH,
    )
