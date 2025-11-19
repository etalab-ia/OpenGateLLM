"""Usage page header component."""

import reflex as rx

from app.core.variables import HEADING_SIZE_PAGE, ICON_SIZE_MEDIUM, MARGIN_MEDIUM
from app.features.usage.state import UsageState


def usage_header() -> rx.Component:
    """Header with title and refresh button."""
    return rx.hstack(
        rx.heading("Usage", size=HEADING_SIZE_PAGE),
        rx.button(
            rx.icon("refresh-cw", size=ICON_SIZE_MEDIUM),
            "Refresh",
            on_click=UsageState.load_usage,
            variant="soft",
            loading=UsageState.loading,
        ),
        width="100%",
        justify="between",
        align="center",
        margin_bottom=MARGIN_MEDIUM,
    )
