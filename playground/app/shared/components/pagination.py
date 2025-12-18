from typing import Any

import reflex as rx

from app.core.variables import SPACING_MEDIUM


def pagination(state: Any) -> rx.Component:
    """Pagination controls for keys list."""
    return rx.hstack(
        rx.button(
            "Prev",
            on_click=state.prev_page,
            disabled=state.current_page <= 1,
        ),
        rx.text(
            state.current_page.to(str),
        ),
        rx.button(
            "Next",
            on_click=state.next_page,
            disabled=~state.has_more_page,
        ),
        spacing=SPACING_MEDIUM,
        align="center",
    )
