"""Limits page header component."""

import reflex as rx


def limits_header() -> rx.Component:
    """Header with title."""
    return rx.hstack(
        rx.heading("Rate Limits", size="8"),
        width="100%",
        justify="between",
        align="center",
        margin_bottom="1em",
    )
