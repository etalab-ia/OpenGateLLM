"""Limits page composition."""

import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.limits.components.headers import limits_header
from app.features.limits.components.lists import limits_list


def limits_page() -> rx.Component:
    """Limits page."""
    return rx.box(
        rx.vstack(
            rx.scroll_area(
                rx.vstack(
                    limits_header(),
                    limits_list(),
                    spacing=SPACING_XL,
                    width="100%",
                    padding=PADDING_PAGE,
                ),
                height="100%",
            ),
            spacing="0",
            width="100%",
            height="100%",
        ),
        flex="1",
        width="100%",
        height="auto",
        background_color=rx.color("mauve", 1),
    )
