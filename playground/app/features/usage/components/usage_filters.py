import reflex as rx

from app.features.usage.state import UsageState


def usage_filters() -> rx.Component:
    """Pagination controls for the table."""
    return rx.hstack(
        rx.heading("Usage details", size="6"),
        rx.spacer(),
        rx.hstack(
            rx.text("Rows per page", size="2"),
            rx.select(
                ["10", "20", "50", "100"],
                value=UsageState.limit_str,
                on_change=UsageState.set_limit,
                size="2",
                width="80px",
            ),
            spacing="2",
            align="center",
        ),
        width="100%",
        align="center",
        spacing="3",
    )
