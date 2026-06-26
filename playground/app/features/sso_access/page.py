import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.sso_access.components.forms import sso_access_policy_form
from app.features.sso_access.components.headers import sso_access_header, sso_inactive_banner


def sso_access_page() -> rx.Component:
    """SSO access policy page."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                sso_access_header(),
                sso_inactive_banner(),
                sso_access_policy_form(),
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
