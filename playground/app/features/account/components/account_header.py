"""Account page header component."""

import reflex as rx

from app.shared.components.headers import header


def account_header() -> rx.Component:
    """Header with title."""
    return header("Account settings")
