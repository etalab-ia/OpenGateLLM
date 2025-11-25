import reflex as rx

from app.features.providers.components.forms import provider_settings_form_fields
from app.features.providers.state import ProvidersState
from app.shared.components.dialogs import entity_delete_dialog, entity_settings_dialog


def provider_settings_dialog() -> rx.Component:
    return entity_settings_dialog(
        state=ProvidersState,
        title="Provider information",
        description="Provider information",
        fields=provider_settings_form_fields(),
    )


def provider_delete_dialog() -> rx.Component:
    return entity_delete_dialog(
        state=ProvidersState,
        title="Delete provider",
        description="Are you sure you want to delete this provider? This action cannot be undone.",
    )
