import reflex as rx


def access_denied_page(message: str) -> rx.Component:
    """Access denied page."""
    return rx.center(
        rx.vstack(
            rx.icon("shield-alert", size=64, color=rx.color("red", 9)),
            rx.heading("Access denied", size="8"),
            rx.text(message, size="4"),
            spacing="4",
        ),
        height="100vh",
    )
