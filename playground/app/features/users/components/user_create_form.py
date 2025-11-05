import reflex as rx

from app.core.variables import HEADING_SIZE_FORM, SIZE_MEDIUM, SPACING_MEDIUM
from app.features.users.components.commons import user_form_fields
from app.features.users.state import UsersState


def user_create_form() -> rx.Component:
    """Form to create a new user."""
    return rx.card(
        rx.vstack(
            rx.heading("Create new user", size=HEADING_SIZE_FORM),
            user_form_fields(
                email_value=UsersState.new_user_email,
                email_on_change=UsersState.set_new_user_email,
                name_value=UsersState.new_user_name,
                name_on_change=UsersState.set_new_user_name,
                password_value=UsersState.new_user_password,
                password_on_change=UsersState.set_new_user_password,
                role_value=UsersState.new_user_role,
                role_on_change=UsersState.set_new_user_role,
                organization_value=UsersState.new_user_organization,
                organization_on_change=UsersState.set_new_user_organization,
                budget_value=UsersState.new_user_budget,
                budget_on_change=UsersState.set_new_user_budget,
                expires_at_value=UsersState.new_user_expires_at,
                expires_at_on_change=UsersState.set_new_user_expires_at,
                priority_value=UsersState.new_user_priority,
                priority_on_change=UsersState.set_new_user_priority,
                available_roles=UsersState.available_roles,
                available_organizations=UsersState.available_organizations,
                disabled=UsersState.create_user_loading,
                password_placeholder="Password",
                password_required=True,
                email_required=True,
            ),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(
                        UsersState.create_user_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Create User",
                    ),
                    on_click=UsersState.create_user,
                    disabled=UsersState.create_user_loading,
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )
