"""API key creation form component."""

import reflex as rx

from app.features.keys.state import KeysState


def keys_create_form() -> rx.Component:
    """Form to create a new API key."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Create new API key", size="6"),
                align="center",
                spacing="2",
            ),
            rx.divider(),
            rx.vstack(
                rx.vstack(
                    rx.text("Key Name", size="2", weight="bold"),
                    rx.input(
                        placeholder="e.g., Production API Key",
                        value=KeysState.new_key_name,
                        on_change=KeysState.set_new_key_name,
                        on_focus=KeysState.clear_errors,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Expires At (optional)", size="2", weight="bold"),
                    rx.input(
                        type="date",
                        value=KeysState.new_key_expires_at_date,
                        on_change=KeysState.set_new_key_expires_at_date,
                        on_focus=KeysState.clear_errors,
                        min=KeysState.min_expiry_date,
                        width="100%",
                    ),
                    rx.text(
                        "Leave empty for no expiration",
                        size="1",
                        color=rx.color("mauve", 9),
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.cond(
                    KeysState.create_key_error != "",
                    rx.callout(
                        KeysState.create_key_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        width="100%",
                    ),
                ),
                rx.button(
                    rx.icon("plus", size=18),
                    "Create API key",
                    on_click=KeysState.create_key,
                    loading=KeysState.create_key_loading,
                    disabled=KeysState.create_key_loading,
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        max_width="1000px",
    )
