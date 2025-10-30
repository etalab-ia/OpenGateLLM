"""Dialog to confirm API key deletion."""

import reflex as rx

from app.features.keys.state import KeysState


def keys_delete_dialog() -> rx.Component:
    """Confirmation dialog for deleting a key."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete API Key"),
            rx.alert_dialog.description(
                "Are you sure you want to delete this API key? This action cannot be undone and will immediately revoke access for this key.",
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Delete",
                        on_click=lambda: KeysState.delete_key(KeysState.key_to_delete),
                        color_scheme="red",
                        loading=KeysState.delete_key_loading,
                    ),
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            spacing="4",
        ),
        open=KeysState.is_delete_dialog_open,
        on_open_change=KeysState.handle_dialog_change,
    )
