"""Roles list component with sorting and pagination."""

import reflex as rx

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
                        size="4",
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
                    spacing="2",
                ),
                rx.hstack(
                    rx.text(
                        f"Created: {role.created_at}",
                        size="2",
                        color=rx.color("mauve", 9),
                    ),
                    rx.text("•", size="2", color=rx.color("mauve", 9)),
                    rx.text(
                        f"Updated: {role.updated_at}",
                        size="2",
                        color=rx.color("mauve", 9),
                    ),
                    spacing="2",
                ),
                rx.hstack(
                    rx.text(
                        role.permissions.length().to(str) + " permission" + rx.cond(role.permissions.length() != 1, "s", ""),
                        size="2",
                        color=rx.color("mauve", 10),
                    ),
                    rx.text("•", size="2", color=rx.color("mauve", 9)),
                    rx.text(
                        role.limits.length().to(str) + " limit" + rx.cond(role.limits.length() != 1, "s", ""),
                        size="2",
                        color=rx.color("mauve", 10),
                    ),
                    spacing="2",
                ),
                spacing="2",
                align_items="start",
                flex="1",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("trash-2", size=18),
                    on_click=lambda: RolesState.set_role_to_delete(role.id),
                    variant="soft",
                    color_scheme="red",
                    size="2",
                ),
                spacing="2",
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
            rx.heading("Create new role", size="4"),
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
                        rx.spinner(size="3"),
                        "Create",
                    ),
                    on_click=RolesState.create_role,
                    disabled=RolesState.create_role_loading,
                ),
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
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
                            rx.spinner(size="3"),
                            "Delete",
                        ),
                        on_click=lambda: RolesState.delete_role(RolesState.role_to_delete),
                        color_scheme="red",
                        disabled=RolesState.delete_role_loading,
                    ),
                ),
                spacing="3",
                justify="end",
            ),
            spacing="4",
        ),
        open=RolesState.is_delete_role_dialog_open,
    )


def roles_sorting() -> rx.Component:
    """Sorting controls for roles."""
    return rx.hstack(
        rx.text("Sort by", size="2", color=rx.color("mauve", 11)),
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
        spacing="2",
        align="center",
    )


def roles_list() -> rx.Component:
    """Display list of roles with sorting and pagination."""
    return rx.vstack(
        create_role_form(),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading("Roles", size="6"),
                    rx.badge(
                        RolesState.roles.length(),
                        variant="soft",
                        color_scheme="blue",
                    ),
                    rx.spacer(),
                    roles_sorting(),
                    align="center",
                    spacing="2",
                    width="100%",
                ),
                rx.divider(),
                rx.cond(
                    RolesState.roles_loading,
                    rx.center(
                        rx.spinner(size="3"),
                        width="100%",
                        padding="2em",
                    ),
                    rx.cond(
                        RolesState.roles.length() > 0,
                        rx.vstack(
                            rx.foreach(RolesState.roles_with_formatted_dates, role_item),
                            spacing="0",
                            width="100%",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("shield", size=48, color=rx.color("mauve", 8)),
                                rx.text(
                                    "No roles yet",
                                    size="4",
                                    color=rx.color("mauve", 10),
                                ),
                                rx.text(
                                    "Create your first role to get started",
                                    size="2",
                                    color=rx.color("mauve", 9),
                                ),
                                spacing="2",
                            ),
                            width="100%",
                            padding="2em",
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
                spacing="3",
                width="100%",
            ),
            width="100%",
        ),
        delete_role_dialog(),
        spacing="4",
        width="100%",
        max_width="1000px",
    )
