"""API key creation form component."""

import reflex as rx

from app.core.variables import ICON_SIZE_TINY, SIZE_MEDIUM, SPACING_MEDIUM, SPACING_TINY, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.keys.state import KeysState


def keys_create_form() -> rx.Component:
    """Form to create a new API key."""
    return rx.card(
        rx.vstack(
            rx.heading("Create new API key", size=TEXT_SIZE_LARGE),
            rx.grid(
                rx.vstack(
                    rx.text("Key name *", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Key name",
                        value=KeysState.new_key_name,
                        on_change=KeysState.set_new_key_name,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Expires at", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.tooltip(
                            rx.icon("info", size=ICON_SIZE_TINY, color=rx.color("mauve", 10)),
                            content=f"The API key will be valid until the specified date and time (maximum: {KeysState.max_expiry_date}).",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.input(
                        type="date",
                        value=KeysState.new_key_expires_at_date,
                        on_change=KeysState.set_new_key_expires_at_date,
                        min=KeysState.min_expiry_date,
                        max=KeysState.max_expiry_date,
                        width="100%",
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
