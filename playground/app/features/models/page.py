"""Models page composition."""

import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.models.components import models_header, models_list


def models_page() -> rx.Component:
    """Models management page with admin permission check."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                models_header(),
                models_list(),
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

