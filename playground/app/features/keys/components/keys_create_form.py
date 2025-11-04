"""API key creation form component."""

import reflex as rx

from app.core.variables import SIZE_MEDIUM, SPACING_MEDIUM, SPACING_TINY, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE, TEXT_SIZE_SMALL
from app.features.keys.state import KeysState


def keys_create_form() -> rx.Component:
    """Form to create a new API key."""
    return rx.card(
        rx.vstack(
            rx.heading("Create new API key", size=TEXT_SIZE_LARGE),
            rx.grid(
                rx.vstack(
                    rx.text("Key Name *", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="e.g., Production API Key",
                        value=KeysState.new_key_name,
                        on_change=KeysState.set_new_key_name,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Expires At (optional)", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        type="date",
                        value=KeysState.new_key_expires_at_date,
                        on_change=KeysState.set_new_key_expires_at_date,
                        min=KeysState.min_expiry_date,
                        width="100%",
                    ),
                    rx.text(
                        "Leave empty for no expiration",
                        size=TEXT_SIZE_SMALL,
                        color=rx.color("mauve", 9),
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                columns="2",
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(KeysState.create_key_loading, rx.spinner(size=SIZE_MEDIUM), "Create"),
                    on_click=KeysState.create_key,
                    disabled=KeysState.create_key_loading,
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )
