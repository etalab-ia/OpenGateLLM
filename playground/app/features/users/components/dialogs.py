import reflex as rx

from app.features.users.components.forms import user_settings_form_fields
from app.features.users.state import UsersState
from app.shared.components.dialogs import entity_delete_dialog, entity_settings_dialog


def user_settings_dialog() -> rx.Component:
    return entity_settings_dialog(
        state=UsersState,
        title="Settings",
        fields=user_settings_form_fields(),
    )


def user_delete_dialog() -> rx.Component:
    return entity_delete_dialog(
        state=UsersState,
        title="Delete user",
        description="Are you sure you want to delete this role? This action cannot be undone.",
    )
