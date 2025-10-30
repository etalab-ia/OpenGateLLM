"""Usage pagination component."""

import reflex as rx

from app.features.usage.state import UsageState


def usage_pagination() -> rx.Component:
    """Pagination controls for usage table."""
    return rx.hstack(
        rx.button(
            "Prev",
            on_click=UsageState.prev_page,
            disabled=UsageState.page <= 1,
        ),
        rx.text(UsageState.page.to(str) + " / " + UsageState.total_pages.to(str)),
        rx.button(
            "Next",
            on_click=UsageState.next_page,
            disabled=~UsageState.has_more,
        ),
        spacing="3",
        align="center",
    )
