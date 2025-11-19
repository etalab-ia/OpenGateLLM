"""Provider delete dialog component."""

import reflex as rx

from app.core.variables import MARGIN_MEDIUM, SIZE_MEDIUM, SPACING_LARGE, SPACING_MEDIUM
from app.features.models.state import ModelsState


def delete_provider_dialog() -> rx.Component:
    """Dialog for deleting a provider."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Provider"),
            rx.alert_dialog.description("Are you sure you want to delete this provider? This action cannot be undone."),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=lambda: ModelsState.set_provider_to_delete(None),
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        rx.cond(
                            ModelsState.delete_provider_loading,
                            rx.spinner(size=SIZE_MEDIUM),
                            "Delete",
                        ),
                        on_click=lambda: ModelsState.delete_provider(ModelsState.provider_to_delete),
                        color_scheme="red",
                        disabled=ModelsState.delete_provider_loading,
                    ),
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
            ),
            spacing=SPACING_LARGE,
        ),
        open=ModelsState.is_delete_provider_dialog_open,
    )

