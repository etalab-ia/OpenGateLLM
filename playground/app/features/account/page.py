import reflex as rx

from app.core.configuration import configuration
from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.account.components import account_header, account_info_card, account_password_card


def account_page() -> rx.Component:
    """Account settings page."""
    children = [account_header(), account_info_card()]
    if configuration.settings.auth_login_type != "oidc":
        children.append(account_password_card())

    return rx.box(
        rx.scroll_area(
            rx.vstack(
                *children,
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
