"""Limits table component."""

import reflex as rx

from app.core.variables import HEADING_SIZE_SECTION, ICON_SIZE_TINY, SPACING_MEDIUM, SPACING_SMALL, SPACING_TINY, TEXT_SIZE_LABEL
from app.features.usage.components.usage_limits_row import usage_limits_row
from app.features.usage.state import UsageState


def usage_limits_table() -> rx.Component:
    """Table displaying rate limits."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Your rate limits", size=HEADING_SIZE_SECTION),
                align="center",
                spacing=SPACING_SMALL,
            ),
            rx.divider(),
            rx.cond(
                UsageState.formatted_limits.length() > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Model"),
                            rx.table.column_header_cell(
                                rx.tooltip(
                                    rx.hstack(
                                        rx.text("RPM"),
                                        rx.icon("info", size=ICON_SIZE_TINY),
                                        spacing=SPACING_TINY,
                                        align="center",
                                    ),
                                    content="Requests Per Minute",
                                ),
                            ),
                            rx.table.column_header_cell(
                                rx.tooltip(
                                    rx.hstack(
                                        rx.text("RPD"),
                                        rx.icon("info", size=ICON_SIZE_TINY),
                                        spacing=SPACING_TINY,
                                        align="center",
                                    ),
                                    content="Requests Per Day",
                                ),
                            ),
                            rx.table.column_header_cell(
                                rx.tooltip(
                                    rx.hstack(
                                        rx.text("TPM"),
                                        rx.icon("info", size=ICON_SIZE_TINY),
                                        spacing=SPACING_TINY,
                                        align="center",
                                    ),
                                    content="Tokens Per Minute",
                                ),
                            ),
                            rx.table.column_header_cell(
                                rx.tooltip(
                                    rx.hstack(
                                        rx.text("TPD"),
                                        rx.icon("info", size=ICON_SIZE_TINY),
                                        spacing=SPACING_TINY,
                                        align="center",
                                    ),
                                    content="Tokens Per Day",
                                ),
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(UsageState.models_list, usage_limits_row),
                    ),
                    variant="surface",
                    width="100%",
                ),
                rx.text(
                    "No rate limits configured",
                    size=TEXT_SIZE_LABEL,
                    color=rx.color("mauve", 9),
                ),
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )
