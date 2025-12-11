"""Usage page composition."""

import reflex as rx

from app.core.configuration import configuration
from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.usage.components.headers import usage_header
from app.features.usage.components.lists import usage_list
from app.shared.components.headers import nav_header


def usage_page() -> rx.Component:
    """Usage page."""
    return rx.vstack(
        nav_header(
            documentation_url=configuration.settings.documentation_url,
            swagger_url=configuration.settings.swagger_url,
            reference_url=configuration.settings.reference_url,
        ),
        rx.box(
            rx.vstack(
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
                spacing="0",
                width="100%",
                height="100%",
            ),
            flex="1",
            width="100%",
            height="100vh",
            background_color=rx.color("mauve", 1),
        ),
        spacing="0",
    )
