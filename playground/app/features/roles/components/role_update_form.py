import reflex as rx

from app.core.variables import MARGIN_MEDIUM, MAX_DIALOG_WIDTH, SIZE_MEDIUM, SPACING_LARGE, SPACING_MEDIUM, SPACING_TINY, TEXT_SIZE_LABEL
from app.features.roles.components.role_create_form import role_permissions_checkboxes
from app.features.roles.state import RolesState


def role_update_form() -> rx.Component:
    """Dialog to update a role."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Edit Role"),
            rx.dialog.description(
                "Update the role name and permissions.",
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
            role_permissions_checkboxes(
                RolesState.edit_role_permissions,
                RolesState.toggle_edit_role_permission,
                RolesState.edit_role_loading,
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
            spacing=SPACING_LARGE,
        ),
        open=RolesState.is_edit_role_dialog_open,
    )
