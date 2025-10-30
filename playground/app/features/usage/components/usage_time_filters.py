"""Usage time range filters component."""

import reflex as rx

from app.features.usage.state import UsageState


def usage_time_filters() -> rx.Component:
    """Time range filters to apply to both table and chart."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text("From", size="2", weight="bold"),
                    rx.input(
                        type="date",
                        value=UsageState.date_from_value,
                        on_change=UsageState.set_date_from,
                        max=UsageState.max_from_date,
                    ),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("To", size="2", weight="bold"),
                    rx.input(
                        type="date",
                        value=UsageState.date_to_value,
                        on_change=UsageState.set_date_to,
                        min=UsageState.min_to_date,
                    ),
                    spacing="1",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("refresh-cw", size=18),
                    "Apply Time Filter",
                    on_click=UsageState.load_usage,
                    variant="soft",
                    align_self="end",
                ),
                width="100%",
                align="end",
                spacing="3",
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        max_width="1000px",
    )
