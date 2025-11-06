"""Login page component."""

import reflex as rx

from app.core.configuration import configuration
from app.features.auth.state import AuthState


def login_page() -> rx.Component:
    """Login page."""
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading(
                    configuration.settings.app_title,
                    size="8",
                    margin_bottom="0.5em",
                ),
                rx.vstack(
                    rx.vstack(
                        rx.text("Email", size="2", weight="bold"),
                        rx.input(
                            placeholder="Enter your email",
                            value=AuthState.email_input,
                            on_change=AuthState.set_email_input,
                            type="email",
                            width="100%",
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Password", size="2", weight="bold"),
                        rx.input(
                            placeholder="Enter your password",
                            value=AuthState.password_input,
                            on_change=AuthState.set_password_input,
                            type="password",
                            width="100%",
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    rx.button(
                        "Sign In",
                        on_click=AuthState.login_direct,
                        width="100%",
                        loading=AuthState.is_loading,
                        disabled=AuthState.is_loading,
                    ),
                    spacing="4",
                    width="100%",
                ),
                spacing="0",
                width="100%",
            ),
            max_width="400px",
            width="100%",
            padding="2em",
        ),
        height="100vh",
        background_color=rx.color("mauve", 1),
    )
