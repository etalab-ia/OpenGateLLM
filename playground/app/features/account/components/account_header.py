"""Account page header component."""

import reflex as rx


def account_header() -> rx.Component:
    """Header with title."""
    return rx.heading(
        "Account settings",
        size="8",
        margin_bottom="1em",
    )
