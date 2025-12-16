"""Authenticated page layout."""

import reflex as rx

from app.core.configuration import configuration
from app.features.auth.components.forms import login_form
from app.features.auth.state import AuthState
from app.features.navigation.components.sidebars import navigation_sidebar
from app.shared.components.headers import nav_header


def authenticated_page(content: rx.Component, margin_left: str | None = "250px", margin_right: str | None = "0px"):
    """Wrap content with authentication check and navigation.

    Args:
        content: The page content to wrap.
        margin_left: The left margin of the content.
        margin_right: The right margin of the content.

    Returns:
        A component with authentication and navigation.
    """

    return rx.cond(
        AuthState.is_authenticated,
        rx.vstack(
            nav_header(
                documentation_url=configuration.settings.documentation_url,
                swagger_url=configuration.settings.swagger_url,
                reference_url=configuration.settings.reference_url,
            ),
            rx.box(
                navigation_sidebar(),
                rx.box(
                    content,
                    position="fixed",
                    top="65px",
                    left=margin_left,
                    right=margin_right,
                    width=f"calc(100% - {margin_left} - {margin_right})",
                    max_height="calc(100vh - 65px)",
                    overflow="auto",
                ),
                display="flex",
            ),
        ),
        login_form(),
    )
