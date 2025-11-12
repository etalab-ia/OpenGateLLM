"""Pagination controls for API keys list."""

import reflex as rx

from app.core.variables import SPACING_MEDIUM
from app.features.keys.state import KeysState


def keys_pagination() -> rx.Component:
    """Pagination controls for keys list."""
    return rx.hstack(
        rx.button(
            "Prev",
            on_click=KeysState.prev_keys_page,
            disabled=KeysState.keys_page <= 1,
        ),
        rx.text(
            KeysState.keys_page.to(str) + " / " + KeysState.keys_total_pages.to(str),
        ),
        rx.button(
            "Next",
            on_click=KeysState.next_keys_page,
            disabled=~KeysState.has_more_keys,
        ),
        spacing=SPACING_MEDIUM,
        align="center",
    )
