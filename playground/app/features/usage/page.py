"""Usage page composition."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    MAX_CARD_WIDTH,
    PADDING_PAGE,
    SPACING_LARGE,
    SPACING_XL,
)
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
                    max_width=MAX_CARD_WIDTH,
                ),
                # Table card
                rx.card(
                    rx.vstack(
                        rx.heading("Usage details", size=HEADING_SIZE_SECTION),
                        usage_table(),
                        rx.hstack(
                            usage_pagination(),
                            width="100%",
                            justify="end",
                        ),
                        spacing=SPACING_LARGE,
                        width="100%",
                    ),
                    width="100%",
                    max_width=MAX_CARD_WIDTH,
                ),
                spacing=SPACING_XL,
                width="100%",
                padding=PADDING_PAGE,
            ),
            height="100%",
        ),
        flex="1",
        width="100%",
        height="100vh",
        background_color=rx.color("mauve", 1),
    )
