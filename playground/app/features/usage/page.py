"""Usage page composition."""

import reflex as rx

from app.features.usage.components import (
    usage_chart,
    usage_header,
    usage_pagination,
    usage_table,
    usage_time_filters,
)


def usage_page() -> rx.Component:
    """Usage tracking page with filters, table, and chart."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                usage_header(),
                # Time filters (apply to both table and chart)
                usage_time_filters(),
                # Chart card
                rx.card(
                    rx.vstack(
                        usage_chart(),
                        width="100%",
                    ),
                    width="100%",
                    max_width="1000px",
                ),
                # Table card
                rx.card(
                    rx.vstack(
                        rx.heading("Usage details", size="6"),
                        usage_table(),
                        rx.hstack(
                            usage_pagination(),
                            width="100%",
                            justify="end",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    width="100%",
                    max_width="1000px",
                ),
                spacing="6",
                width="100%",
                padding="2em",
            ),
            height="100%",
        ),
        flex="1",
        width="100%",
        height="100vh",
        background_color=rx.color("mauve", 1),
    )
