import reflex as rx

from app.core.configuration import configuration
from app.features.auth.state import UNAUTHORIZED_TOAST_DURATION_MS, AuthState


def password_login_form():
    """Password login form."""
    return rx.vstack(
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
                on_click=AuthState.basic_login,
                width="100%",
                loading=AuthState.is_loading,
                disabled=AuthState.is_loading,
                cursor="pointer",
            ),
            spacing="4",
            width="100%",
        ),
        spacing="0",
        width="100%",
    )


def oidc_login_form() -> rx.Component:
    """OIDC login form."""
    return rx.vstack(
        rx.vstack(
            rx.vstack(
                rx.vstack(
                    rx.text("Login processing, you will be redirected soon...", size="2"),
                    rx.cond(
                        AuthState.is_loading,
                        rx.cond(
                            AuthState.has_access,
                            rx.progress(
                                duration=f"{configuration.settings.playground_opengatellm_timeout}s",
                                size="3",
                                width="100%",
                            ),
                            rx.progress(
                                duration=f"{UNAUTHORIZED_TOAST_DURATION_MS}ms",
                                size="3",
                                width="100%",
                            ),
                        ),
                    ),
                    spacing="3",
                    width="100%",
                    align="center",
                ),
                spacing="4",
                width="100%",
                align="center",
            ),
            rx.spacer(),
            rx.divider(),
            rx.button(
                "If your are not automatically redirected, click here.",
                on_click=AuthState.oidc_logout,
                width="100%",
                loading=AuthState.is_loading,
                disabled=AuthState.is_loading,
                cursor="pointer",
                variant="soft",
                color_scheme="gray",
                size="1",
            ),
            spacing="4",
            width="100%",
        ),
        spacing="0",
        width="100%",
    )
