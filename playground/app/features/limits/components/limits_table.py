"""Limits table component."""

import reflex as rx

from app.features.limits.components.limits_row import limits_row
from app.features.limits.state import LimitsState


def limits_table() -> rx.Component:
    """Table displaying rate limits."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Your rate limits", size="6"),
                align="center",
                spacing="2",
            ),
            rx.divider(),
            rx.cond(
                LimitsState.formatted_limits.length() > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Model"),
                            rx.table.column_header_cell(
                                rx.tooltip(
                                    rx.hstack(
                                        rx.text("RPM"),
                                        rx.icon("info", size=14),
                                        spacing="1",
                                        align="center",
                                    ),
                                    content="Requests Per Minute",
                                ),
                            ),
                            rx.table.column_header_cell(
                                rx.tooltip(
                                    rx.hstack(
                                        rx.text("RPD"),
                                        rx.icon("info", size=14),
                                        spacing="1",
                                        align="center",
                                    ),
                                    content="Requests Per Day",
                                ),
                            ),
                            rx.table.column_header_cell(
                                rx.tooltip(
                                    rx.hstack(
                                        rx.text("TPM"),
                                        rx.icon("info", size=14),
                                        spacing="1",
                                        align="center",
                                    ),
                                    content="Tokens Per Minute",
                                ),
                            ),
                            rx.table.column_header_cell(
                                rx.tooltip(
                                    rx.hstack(
                                        rx.text("TPD"),
                                        rx.icon("info", size=14),
                                        spacing="1",
                                        align="center",
                                    ),
                                    content="Tokens Per Day",
                                ),
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(LimitsState.models_list, limits_row),
                    ),
                    variant="surface",
                    width="100%",
                ),
                rx.text(
                    "No rate limits configured",
                    size="2",
                    color=rx.color("mauve", 9),
                ),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        max_width="1000px",
    )
