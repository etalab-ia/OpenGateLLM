import reflex as rx

from app.core.configuration import configuration
from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.roles.components.forms import role_create_form
from app.features.roles.components.headers import roles_header
from app.features.roles.components.lists import roles_list
from app.shared.components.headers import nav_header


def roles_page() -> rx.Component:
    """Roles management page."""
    return rx.vstack(
        nav_header(
            documentation_url=configuration.settings.documentation_url,
            swagger_url=configuration.settings.swagger_url,
            reference_url=configuration.settings.reference_url,
        ),
        rx.box(
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
        ),
        spacing="0",
    )
