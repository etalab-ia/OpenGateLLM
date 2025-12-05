"""Usage page composition."""

import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.usage.components.headers import usage_header
from app.features.usage.components.lists import usage_list


def usage_page() -> rx.Component:
    """Usage page."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                usage_header(),
                usage_list(),
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
