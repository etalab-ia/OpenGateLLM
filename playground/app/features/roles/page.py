import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.roles.components import (
    role_create_form,
    roles_header,
    roles_list,
)


def roles_page() -> rx.Component:
    """Roles management page with admin permission check."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                roles_header(),
                role_create_form(),
                roles_list(),
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
