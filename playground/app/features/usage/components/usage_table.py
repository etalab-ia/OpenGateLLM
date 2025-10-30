"""Usage table component."""

import reflex as rx

from app.features.usage.state import UsageState


def usage_table() -> rx.Component:
    """Table displaying usage data."""
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Datetime"),
                rx.table.column_header_cell("Endpoint"),
                rx.table.column_header_cell("Model"),
                rx.table.column_header_cell("Tokens"),
                rx.table.column_header_cell("Cost"),
            ),
        ),
        rx.table.body(
            rx.foreach(
                UsageState.usage_rows,
                lambda row: rx.table.row(
                    rx.table.cell(row["datetime"]),
                    rx.table.cell(row["endpoint"]),
                    rx.table.cell(row["model"]),
                    rx.table.cell(row["tokens"]),
                    rx.table.cell(row["cost"]),
                ),
            ),
        ),
        variant="surface",
        width="100%",
    )
