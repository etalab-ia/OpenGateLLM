"""Account page header component."""

import reflex as rx

from app.core.variables import HEADING_SIZE_PAGE, HEADING_WEIGHT, MARGIN_MEDIUM


def account_header() -> rx.Component:
    """Header with title."""
    return rx.heading(
        "Account settings",
        size=HEADING_SIZE_PAGE,
        weight=HEADING_WEIGHT,
        margin_bottom=MARGIN_MEDIUM,
    )
