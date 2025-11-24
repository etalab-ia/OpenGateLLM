import reflex as rx

from app.features.routers.components.forms import router_edit_form_fields
from app.features.routers.state import RoutersState
from app.shared.components.dialogs import entity_delete_dialog, entity_edit_dialog


def router_edit_dialog() -> rx.Component:
    return entity_edit_dialog(
        state=RoutersState,
        title="Edit router",
        fields=router_edit_form_fields(),
    )


def router_delete_dialog() -> rx.Component:
    return entity_delete_dialog(
        state=RoutersState,
        title="Delete Router",
        description="Are you sure you want to delete this router? This action cannot be undone.",
    )
