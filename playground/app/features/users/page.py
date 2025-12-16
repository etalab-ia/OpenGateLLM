import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.users.components.forms import user_create_form
from app.features.users.components.headers import users_header
from app.features.users.components.lists import users_list


def users_page() -> rx.Component:
    """Users management page."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                users_header(),
                user_create_form(),
                users_list(),
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
