"""Keys page composition."""

import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.keys.components import (
    keys_create_form,
    keys_created_dialog,
    keys_delete_dialog,
    keys_header,
    keys_list,
)


def keys_page() -> rx.Component:
    """API Keys management page."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                keys_header(),
                keys_create_form(),
                keys_list(),
                spacing=SPACING_XL,
                width="100%",
                padding=PADDING_PAGE,
            ),
            height="100%",
        ),
        keys_created_dialog(),
        keys_delete_dialog(),
        flex="1",
        width="100%",
        height="100vh",
        background_color=rx.color("mauve", 1),
    )
