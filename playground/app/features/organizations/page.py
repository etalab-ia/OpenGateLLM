import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.organizations.components.forms import organization_create_form
from app.features.organizations.components.headers import organizations_header
from app.features.organizations.components.lists import organizations_list


def organizations_page() -> rx.Component:
    """Organizations management page."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                organizations_header(),
                organization_create_form(),
                organizations_list(),
                spacing=SPACING_XL,
                width="100%",
                padding=PADDING_PAGE,
            ),
            height="100%",
        ),
        flex="1",
        width="100%",
        height="auto",
        background_color=rx.color("mauve", 1),
    )
