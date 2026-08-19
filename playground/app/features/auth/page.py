import reflex as rx

from app.core.configuration import configuration
from app.features.auth.state import AuthState


def admin_deny_page() -> rx.Component:
    """Access denied page."""
    return rx.center(
        rx.vstack(
            rx.icon("circle_x", size=64, color=rx.color("mauve", 11)),
            rx.heading("Access denied", size="8"),
            rx.text("You need admin permissions to access this page.", size="4"),
            spacing="4",
            align="center",
        ),
        height="100vh",
    )


def sso_deny_page() -> rx.Component:
    """Access denied page."""

    app_title = configuration.settings.app_title
    documentation_url = configuration.settings.playground_sso_access_denied_documentation_url
    return rx.center(
        rx.vstack(
            rx.icon("circle_x", size=64, color=rx.color("mauve", 11)),
            rx.heading("Access denied", size="8"),
            rx.cond(
                documentation_url is not None,
                rx.text(
                    f"Your account is not authorized to access to {app_title}. See ",
                    rx.link(
                        "documentation",
                        href=documentation_url,
                        target="_blank",
                    ),
                    " for more information.",
                    size="4",
                ),
                rx.text("Your account is not authorized to access.", size="4"),
            ),
            rx.button(
                rx.icon("log-out", size=20),
                "Logout",
                on_click=AuthState.oidc_logout,
                variant="soft",
                color_scheme="red",
                size="4",
            ),
            spacing="4",
            align="center",
        ),
        height="100vh",
    )


def sso_error_page() -> rx.Component:
    """SSO unexpected error page."""
    return rx.center(
        rx.vstack(
            rx.icon("traffic_cone", size=64, color=rx.color("mauve", 11)),
            rx.heading("Something went wrong", size="8"),
            rx.text(
                rx.cond(
                    AuthState.auth_error_message != "",
                    AuthState.auth_error_message,
                    "An unexpected error occurred. Please try again later.",
                ),
                size="4",
            ),
            rx.button(
                rx.icon("log-out", size=20),
                "Logout",
                on_click=AuthState.oidc_logout,
                variant="soft",
                color_scheme="red",
                size="4",
            ),
            spacing="4",
            align="center",
        ),
        height="100vh",
    )
