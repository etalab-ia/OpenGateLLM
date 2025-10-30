"""Account page composition."""

import reflex as rx

from app.features.account.components import (
    account_header,
    account_info_card,
    account_security_card,
)


def account_page() -> rx.Component:
    """Account settings page."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                account_header(),
                account_info_card(),
                account_security_card(),
                spacing="6",
                width="100%",
                padding="2em",
            ),
            height="100%",
        ),
        flex="1",
        width="100%",
        height="100vh",
        background_color=rx.color("mauve", 1),
    )
