"""Roles page header component."""

import reflex as rx


def roles_header() -> rx.Component:
    """Header for roles management page."""
    return rx.hstack(
        rx.heading("Roles management", size="8"),
        rx.badge(
            rx.hstack(
                rx.icon("shield-check", size=16),
                rx.text("Admin", size="2"),
                spacing="1",
                align="center",
            ),
            color_scheme="red",
            variant="soft",
            size="3",
        ),
        align="center",
        spacing="3",
        width="100%",
        margin_bottom="1em",
    )
