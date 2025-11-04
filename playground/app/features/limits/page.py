"""Limits page composition."""

import reflex as rx

from app.core.variables import (
    PADDING_PAGE,
    SPACING_XL,
)
from app.features.limits.components import limits_header, limits_table


def limits_page() -> rx.Component:
    """Rate limits page."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                limits_header(),
                limits_table(),
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
