import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.providers.components.forms import provider_create_form
from app.features.providers.components.headers import providers_header
from app.features.providers.components.lists import providers_list


def providers_page() -> rx.Component:
    """Providers management page."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                providers_header(),
                provider_create_form(),
                providers_list(),
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
