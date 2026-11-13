"""Limits page composition."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    PADDING_PAGE,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
)
from app.features.limits.models import Limit, ModelLimits
from app.features.limits.state import LimitsState


def limit_row(limit: Limit) -> rx.Component:
    """One rate limit of a model."""
    return rx.table.row(
        rx.table.cell(
            rx.text(limit.type_label, size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        ),
        rx.table.cell(
            rx.cond(
                limit.is_unlimited,
                rx.fragment(),
                rx.hstack(
                    rx.progress(value=limit.percent),
                    rx.text(limit.percent.to(str) + "%", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11), min_width="3em", text_align="right"),
                    spacing=SPACING_MEDIUM,
                    align="center",
                    width="100%",
                ),
            ),
        ),
        rx.table.cell(
            rx.cond(
                limit.is_unlimited,
                rx.text("Unlimited", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
                rx.text(
                    rx.text.span(limit.used, weight="medium", color=rx.color("mauve", 12)),
                    rx.text.span(" / " + limit.value, color=rx.color("mauve", 11)),
                    size=TEXT_SIZE_LABEL,
                ),
            ),
            justify="end",
        ),
        align="center",
    )


def model_limits_rows(model_limits: ModelLimits) -> rx.Component:
    """Model header row followed by the rows of its limits."""
    return rx.fragment(
        rx.table.row(
            rx.table.cell(
                rx.text(model_limits.model, size=TEXT_SIZE_LABEL, weight="medium", color=rx.color("mauve", 12)),
                col_span=3,
                padding_top="var(--space-5)",
            ),
        ),
        rx.foreach(model_limits.limits, limit_row),
    )


def limits_table() -> rx.Component:
    """Rate limits grouped by allowed model, with what is used of each."""
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Limit"),
                rx.table.column_header_cell("Current usage", width="35%"),
                rx.table.column_header_cell("Used / limit", justify="end"),
            ),
        ),
        rx.table.body(rx.foreach(LimitsState.entities, model_limits_rows)),
        width="100%",
    )


def limits_list() -> rx.Component:
    """Card holding the limits table, a spinner while loading, or an empty state."""
    return rx.card(
        rx.vstack(
            rx.vstack(
                rx.heading("Rate limits", size=HEADING_SIZE_SECTION),
                rx.text(
                    "Your rate limits on each model and what you have used of them. Limits reset per minute (RPM, TPM) or per day (RPD, TPD).",
                    size=TEXT_SIZE_LABEL,
                    color=rx.color("mauve", 11),
                ),
                spacing=SPACING_TINY,
            ),
            rx.divider(),
            rx.cond(
                # Only the first load shows the spinner: a refresh updates the table in place.
                LimitsState.entities_loading & (LimitsState.entities.length() == 0),
                rx.center(
                    rx.spinner(size=SIZE_MEDIUM),
                    width="100%",
                    padding=PADDING_PAGE,
                ),
                rx.cond(
                    LimitsState.entities.length() > 0,
                    limits_table(),
                    rx.text("You are not allowed to use any model yet.", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
                ),
            ),
            spacing=SPACING_LARGE,
            width="100%",
        ),
        width="100%",
    )
