"""Account security card component."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    MARGIN_SMALL,
    MAX_CARD_WIDTH,
    SPACING_MEDIUM,
)
from app.features.account.components.account_password_dialog import (
    account_password_dialog,
)


def account_security_card() -> rx.Component:
    """Card with security options."""
    return rx.card(
        rx.vstack(
            rx.heading(
                "Security",
                size=HEADING_SIZE_SECTION,
                margin_bottom=MARGIN_SMALL,
            ),
            rx.divider(),
            account_password_dialog(),
            spacing=SPACING_MEDIUM,
            width="100%",
            align_items="start",
        ),
        width="100%",
        max_width=MAX_CARD_WIDTH,
    )
