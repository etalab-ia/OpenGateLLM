import reflex as rx

from app.core.variables import (
    HEADING_SIZE_FORM,
    SIZE_MEDIUM,
    SPACING_MEDIUM,
    SPACING_SMALL,
    TEXT_SIZE_MEDIUM,
)
from app.features.roles.components.commons import permission_checkbox_item
from app.features.roles.state import RolesState


def role_permissions_checkboxes(permissions_list, toggle_handler, disabled: bool = False):
    """Checkboxes for role permissions - generalized for create and edit."""
    return rx.vstack(
        rx.heading("Special permissions", size=TEXT_SIZE_MEDIUM),
        permission_checkbox_item(
            "admin",
            "Admin",
            "Give admistration rights to manage users, roles, and permissions.",
            permissions_list,
            toggle_handler,
            disabled,
        ),
        permission_checkbox_item(
            "create_public_collection",
            "Create public collection",
            "Allow creating public collections. Public collections are visible to all users.",
            permissions_list,
            toggle_handler,
            disabled,
        ),
        permission_checkbox_item(
            "read_metric",
            "Read metrics",
            "Allow reading Prometheus metrics (by /metrics endpoint).",
            permissions_list,
            toggle_handler,
            disabled,
        ),
        permission_checkbox_item(
            "provide_models",
            "Provide models",
            "Allow add and remove model providers for the model routers.",
            permissions_list,
            toggle_handler,
            disabled,
        ),
        spacing=SPACING_SMALL,
        width="100%",
    )


def role_create_form() -> rx.Component:
    """Form to create a new role."""
    return rx.card(
        rx.vstack(
            rx.heading("Create new role", size=HEADING_SIZE_FORM),
            rx.heading("Role name", size=TEXT_SIZE_MEDIUM),
            rx.input(
                placeholder="Role name",
                value=RolesState.new_role_name,
                on_change=RolesState.set_new_role_name,
                disabled=RolesState.create_role_loading,
                width="100%",
            ),
            role_permissions_checkboxes(
                RolesState.new_role_permissions,
                RolesState.toggle_new_role_permission,
                RolesState.create_role_loading,
            ),
            rx.hstack(
                rx.spacer(),
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
