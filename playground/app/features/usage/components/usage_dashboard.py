"""Usage page composition."""

import reflex as rx

from app.core.variables import HEADING_SIZE_SECTION, SPACING_LARGE, SPACING_SMALL, TEXT_SIZE_LABEL
from app.features.usage.components.usage_chart import usage_chart
from app.features.usage.components.usage_pagination import usage_pagination
from app.features.usage.components.usage_table import usage_table
from app.features.usage.state import UsageState


def usage_dashboard() -> rx.Component:
    """Usage tracking page with filters, table, and chart."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Requests details", size=HEADING_SIZE_SECTION),
                rx.spacer(),
                rx.text("From", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
                rx.input(
                    type="date",
                    value=UsageState.date_from_value,
                    on_change=UsageState.set_date_from,
                    max=UsageState.max_from_date,
                ),
                rx.text("To", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
                rx.input(
                    type="date",
                    value=UsageState.date_to_value,
                    on_change=UsageState.set_date_to,
                    min=UsageState.min_to_date,
                ),
                rx.button(
                    "Apply",
                    on_click=UsageState.load_usage,
                    align_self="end",
                ),
                align="center",
                spacing=SPACING_SMALL,
                width="100%",
            ),
            rx.divider(),
            rx.spacer(size="10"),
            usage_chart(),
            rx.vstack(
                usage_table(),
                rx.hstack(usage_pagination(), width="100%", justify="end"),
                spacing=SPACING_LARGE,
                width="100%",
            ),
        ),
        width="100%",
        spacing=SPACING_LARGE,
    )
