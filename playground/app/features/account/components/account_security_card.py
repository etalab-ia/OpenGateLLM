"""Account security card component."""

import reflex as rx

from app.features.account.components.account_password_dialog import (
    account_password_dialog,
)


def account_security_card() -> rx.Component:
    """Card with security options."""
    return rx.card(
        rx.vstack(
            rx.heading(
                "Security",
                size="6",
                margin_bottom="0.5em",
            ),
            rx.divider(),
            account_password_dialog(),
            spacing="3",
            width="100%",
            align_items="start",
        ),
        width="100%",
        max_width="1000px",
    )
