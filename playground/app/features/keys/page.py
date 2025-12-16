import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.keys.components.dialogs import keys_created_dialog
from app.features.keys.components.forms import keys_create_form
from app.features.keys.components.headers import keys_header
from app.features.keys.components.lists import keys_list


def keys_page() -> rx.Component:
    """Roles management page."""
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
        flex="1",
        width="100%",
        height="auto",
        background_color=rx.color("mauve", 1),
    )
