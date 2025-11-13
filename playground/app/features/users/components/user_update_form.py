import reflex as rx

from app.core.variables import MARGIN_MEDIUM, MAX_DIALOG_WIDTH, SIZE_MEDIUM, SPACING_LARGE, SPACING_MEDIUM
from app.features.users.components.commons import user_form_fields
from app.features.users.state import UsersState


def user_update_form() -> rx.Component:
    """Dialog to update a user."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Edit User"),
            rx.dialog.description(
                "Update user information. Leave fields empty to keep current values.",
            ),
            user_form_fields(
                email_value=UsersState.edit_user_email,
                email_on_change=UsersState.set_edit_user_email,
                name_value=UsersState.edit_user_name,
                name_on_change=UsersState.set_edit_user_name,
                password_value=UsersState.edit_user_password,
                password_on_change=UsersState.set_edit_user_password,
                role_value=UsersState.edit_user_role,
                role_on_change=UsersState.set_edit_user_role,
                organization_value=UsersState.edit_user_organization,
                organization_on_change=UsersState.set_edit_user_organization,
                budget_value=UsersState.edit_user_budget,
                budget_on_change=UsersState.set_edit_user_budget,
                expires_value=UsersState.edit_user_expires,
                expires_on_change=UsersState.set_edit_user_expires,
                priority_value=UsersState.edit_user_priority,
                priority_on_change=UsersState.set_edit_user_priority,
                available_roles=UsersState.available_roles,
                available_organizations=UsersState.available_organizations,
                disabled=UsersState.edit_user_loading,
                password_placeholder="Leave empty to keep current",
                password_required=False,
                email_required=False,
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=lambda: UsersState.set_user_to_edit(None),
                    ),
                ),
                rx.button(
                    rx.cond(
                        UsersState.edit_user_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Update",
                    ),
                    on_click=UsersState.update_user,
                    disabled=UsersState.edit_user_loading,
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
                margin_top=MARGIN_MEDIUM,
            ),
            max_width=MAX_DIALOG_WIDTH,
            spacing=SPACING_LARGE,
        ),
        open=UsersState.is_edit_user_dialog_open,
    )
