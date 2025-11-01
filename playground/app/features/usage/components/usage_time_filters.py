"""Usage time range filters component."""

import reflex as rx

from app.core.variables import (
    ICON_SIZE_MEDIUM,
    MAX_CARD_WIDTH,
    SPACING_MEDIUM,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
)
from app.features.usage.state import UsageState


def usage_time_filters() -> rx.Component:
    """Time range filters to apply to both table and chart."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text("From", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        type="date",
                        value=UsageState.date_from_value,
                        on_change=UsageState.set_date_from,
                        max=UsageState.max_from_date,
                    ),
                    spacing=SPACING_TINY,
                ),
                rx.vstack(
                    rx.text("To", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        type="date",
                        value=UsageState.date_to_value,
                        on_change=UsageState.set_date_to,
                        min=UsageState.min_to_date,
                    ),
                    spacing=SPACING_TINY,
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("refresh-cw", size=ICON_SIZE_MEDIUM),
                    "Apply Time Filter",
                    on_click=UsageState.load_usage,
                    variant="soft",
                    align_self="end",
                ),
                width="100%",
                align="end",
                spacing=SPACING_MEDIUM,
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
        max_width=MAX_CARD_WIDTH,
    )
