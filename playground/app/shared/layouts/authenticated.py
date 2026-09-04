"""Authenticated page layout."""

import reflex as rx

from app.features.auth.components.cards import login_card
from app.features.auth.components.forms import oidc_login_form, password_login_form
from app.features.auth.state import AuthState
from app.features.navigation.components.sidebars import navigation_sidebar


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
        rx.box(
            navigation_sidebar(),
            rx.box(
                content,
                position="fixed",
                top="0",
                left=margin_left,
                right=margin_right,
                width=f"calc(100% - {margin_left} - {margin_right})",
                height="100vh",
                overflow="auto",
            ),
            display="flex",
        ),
        rx.cond(
            AuthState.login_type == "oidc",
            login_card(login_form=oidc_login_form()),
            login_card(login_form=password_login_form()),
        ),
    )
