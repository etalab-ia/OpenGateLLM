import reflex as rx

from app.features.providers.components.forms import provider_info_form_fields
from app.features.providers.state import ProvidersState
from app.shared.components.dialogs import entity_delete_dialog, entity_info_dialog


def provider_info_dialog() -> rx.Component:
    return entity_info_dialog(
        state=ProvidersState,
        title="Provider information",
        description="Provider information",
        fields=provider_info_form_fields(),
    )


def provider_delete_dialog() -> rx.Component:
    return entity_delete_dialog(
        state=ProvidersState,
        title="Delete provider",
        description="Are you sure you want to delete this provider? This action cannot be undone.",
    )
