import reflex as rx

from app.features.organizations.components.forms import organization_settings_form_fields
from app.features.organizations.state import OrganizationsState
from app.shared.components.dialogs import entity_delete_dialog, entity_settings_dialog


def organization_settings_dialog() -> rx.Component:
    return entity_settings_dialog(
        state=OrganizationsState,
        title="Settings",
        fields=organization_settings_form_fields(),
    )


def organization_delete_dialog() -> rx.Component:
    return entity_delete_dialog(
        state=OrganizationsState,
        title="Delete organization",
        description="Are you sure you want to delete this organization? This action cannot be undone.",
    )
