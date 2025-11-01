"""Limits page header component."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_PAGE,
    MARGIN_MEDIUM,
)


def limits_header() -> rx.Component:
    """Header with title."""
    return rx.hstack(
        rx.heading("Rate limits", size=HEADING_SIZE_PAGE),
        width="100%",
        justify="between",
        align="center",
        margin_bottom=MARGIN_MEDIUM,
    )
