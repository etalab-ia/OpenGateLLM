import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.account.components import account_header, account_info_card, account_password_card


def account_page() -> rx.Component:
    """Account settings page."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                account_header(),
                account_info_card(),
                account_password_card(),
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
