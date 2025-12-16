"""Usage page composition."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    ICON_SIZE_TINY,
    SELECT_MEDIUM_WIDTH,
    SPACING_LARGE,
    SPACING_SMALL,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
)
from app.features.usage.state import UsageState
from app.shared.components.pagination import pagination


def usage_filters() -> rx.Component:
    """Filters for usage list."""
    return (
        rx.hstack(
            rx.text("Filters", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
            rx.select(
                UsageState.endpoints_name_list,
                on_change=UsageState.set_filter_endpoint,
                value=UsageState.filter_endpoint_value,
                width=SELECT_MEDIUM_WIDTH,
            ),
            rx.text("From", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
            rx.input(
                type="date",
                value=UsageState.get_filter_date_from_value,
                on_change=UsageState.set_filter_date_from,
                max=UsageState.filter_date_to_value_max,
            ),
            rx.text("To", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
            rx.input(
                type="date",
                value=UsageState.get_filter_date_to_value,
                on_change=UsageState.set_filter_date_to,
            ),
            rx.button(
                "Apply",
                on_click=UsageState.apply_filters,
                align_self="end",
            ),
            spacing=SPACING_SMALL,
            align="center",
        ),
    )


def usage_table() -> rx.Component:
    """Table displaying usage data."""
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Date", width="140px"),
                rx.table.column_header_cell("Key", width="120px"),
                rx.table.column_header_cell("Endpoint", width="200px"),
                rx.table.column_header_cell("Model", width="150px"),
                rx.table.column_header_cell("Tokens", width="120px"),
                rx.table.column_header_cell("Cost", width="100px"),
                rx.table.column_header_cell(
                    rx.tooltip(
                        rx.hstack(
                            rx.text("Carbon"),
                            rx.icon("info", size=ICON_SIZE_TINY),
                            spacing=SPACING_TINY,
                            align="center",
                        ),
                        content="Carbon footprint in kgCO2eq (Global warming potential)",
                    ),
                    width="150px",
                ),
            ),
        ),
        rx.table.body(
            rx.foreach(
                UsageState.usage_rows,
                lambda row: rx.table.row(
                    rx.table.cell(row["date"], width="140px"),
                    rx.table.cell(row["key"], width="120px"),
                    rx.table.cell(row["endpoint"], width="200px"),
                    rx.table.cell(row["model"], width="150px"),
                    rx.table.cell(row["tokens"], width="120px"),
                    rx.table.cell(row["cost"], width="100px"),
                    rx.table.cell(row["kgCO2eq"], width="150px"),
                ),
            ),
        ),
        variant="surface",
        width="100%",
        style={"table-layout": "fixed"},
    )


def usage_list() -> rx.Component:
    """Usage tracking page with filters, table, and chart."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Requests details", size=HEADING_SIZE_SECTION),
                rx.spacer(),
                usage_filters(),
                align="center",
                spacing=SPACING_SMALL,
                width="100%",
            ),
            rx.divider(),
            rx.spacer(size="10"),
            rx.vstack(
                usage_table(),
                rx.hstack(pagination(state=UsageState), width="100%", justify="end"),
                spacing=SPACING_LARGE,
                width="100%",
            ),
        ),
        width="100%",
        spacing=SPACING_LARGE,
    )
