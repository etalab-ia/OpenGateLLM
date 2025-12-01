import reflex as rx

from app.features.roles.components.forms import role_settings_form_fields
from app.features.roles.state import RolesState
from app.shared.components.dialogs import entity_delete_dialog, entity_settings_dialog


def role_settings_dialog() -> rx.Component:
    return entity_settings_dialog(
        state=RolesState,
        title="Settings",
        fields=role_settings_form_fields(),
    )


def role_delete_dialog() -> rx.Component:
    return entity_delete_dialog(
        state=RolesState,
        title="Delete role",
        description="Are you sure you want to delete this role? This action cannot be undone.",
    )
