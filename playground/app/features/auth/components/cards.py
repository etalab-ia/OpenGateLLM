import reflex as rx

from app.core.configuration import configuration


def login_card(login_form: rx.Component) -> rx.Component:
    """Login page."""
    return rx.center(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.image(
                        src="/logo.svg",
                        width="32px",
                        height="32px",
                    ),
                    rx.heading(
                        configuration.settings.app_title,
                        size="8",
                    ),
                    spacing="2",
                    width="100%",
                    align_items="center",
                    justify_content="center",
                    margin_top="1em",
                    margin_bottom="2em",
                ),
                spacing="0",
                width="100%",
            ),
            login_form,
            max_width="400px",
            width="100%",
            padding="2em",
        ),
        height="100vh",
        background_color=rx.color("mauve", 1),
    )
