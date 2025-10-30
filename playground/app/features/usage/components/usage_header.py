"""Usage page header component."""

import reflex as rx

from app.features.usage.state import UsageState


def usage_header() -> rx.Component:
    """Header with title and refresh button."""
    return rx.hstack(
        rx.heading("Usage", size="8"),
        rx.button(
            rx.icon("refresh-cw", size=18),
            "Refresh",
            on_click=UsageState.load_usage,
            variant="soft",
            loading=UsageState.loading,
        ),
        width="100%",
        justify="between",
        align="center",
        margin_bottom="1em",
    )
