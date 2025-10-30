"""Roles permissions management component."""

import reflex as rx

from app.features.roles.state import RolesState


def permission_row(permission: str) -> rx.Component:
    """Display a single permission row."""
    return rx.table.row(
        rx.table.cell(
            rx.text(
                permission,
                size="3",
                weight="medium",
                color=rx.color("mauve", 12),
            ),
        ),
        rx.table.cell(
            rx.button(
                rx.icon("trash-2", size=18),
                on_click=lambda: RolesState.delete_permission(permission),
                variant="soft",
                color_scheme="red",
                size="2",
                disabled=RolesState.delete_permission_loading,
            ),
            justify="end",
        ),
        align="center",
    )


def add_permission_form() -> rx.Component:
    """Form to add a new permission."""
    return rx.vstack(
        rx.hstack(
            rx.select(
                RolesState.available_permissions_to_add,
                placeholder="Select permission",
                value=RolesState.new_permission,
                on_change=RolesState.set_new_permission,
                disabled=RolesState.add_permission_loading,
                flex="1",
            ),
            rx.button(
                rx.cond(
                    RolesState.add_permission_loading,
                    rx.spinner(size="3"),
                    "Add",
                ),
                on_click=RolesState.add_permission,
                disabled=RolesState.add_permission_loading | ~RolesState.has_permissions_selected_role,
            ),
            width="100%",
            spacing="2",
        ),
        spacing="3",
        width="100%",
    )


def roles_permissions() -> rx.Component:
    """Display and manage permissions for selected role."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Permissions", size="6"),
                rx.spacer(),
                rx.text("Role", size="2", color=rx.color("mauve", 11)),
                rx.select.root(
                    rx.select.trigger(placeholder="Select a role", size="2", width="200px"),
                    rx.select.content(
                        rx.foreach(
                            RolesState.roles,
                            lambda role: rx.select.item(role.name, value=role.id.to(str)),
                        ),
                    ),
                    value=rx.cond(
                        RolesState.permissions_selected_role_id,
                        RolesState.permissions_selected_role_id.to(str),
                        "",
                    ),
                    on_change=RolesState.set_permissions_selected_role,
                ),
                align="center",
                spacing="2",
                width="100%",
            ),
            rx.divider(),
            rx.cond(
                ~RolesState.has_permissions_selected_role,
                rx.center(
                    rx.vstack(
                        rx.icon("arrow-up", size=48, color=rx.color("mauve", 8)),
                        rx.text(
                            "Select a role first",
                            size="4",
                            color=rx.color("mauve", 10),
                        ),
                        rx.text(
                            "Choose a role from the dropdown above to manage its permissions",
                            size="2",
                            color=rx.color("mauve", 9),
                        ),
                        spacing="2",
                    ),
                    width="100%",
                    padding="2em",
                ),
                rx.cond(
                    RolesState.selected_role_permissions.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Permission", min_width="400px"),
                                rx.table.column_header_cell(justify="end", min_width="100px"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(RolesState.selected_role_permissions, permission_row),
                        ),
                        variant="surface",
                        width="100%",
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon("shield-off", size=48, color=rx.color("mauve", 8)),
                            rx.text(
                                "No permissions",
                                size="4",
                                color=rx.color("mauve", 10),
                            ),
                            rx.text(
                                "This role has no permissions configured",
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
            add_permission_form(),
            spacing="3",
            width="100%",
        ),
        width="100%",
        max_width="1000px",
    )
