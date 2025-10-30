"""Keys page header component."""

import reflex as rx

from app.features.keys.state import KeysState


def keys_header() -> rx.Component:
    """Header with title and refresh button."""
    return rx.hstack(
        rx.heading("API Keys", size="8"),
        rx.button(
            rx.icon("refresh-cw", size=18),
            "Refresh",
            on_click=KeysState.load_keys,
            variant="soft",
            loading=KeysState.keys_loading,
        ),
        width="100%",
        justify="between",
        align="center",
        margin_bottom="1em",
    )
