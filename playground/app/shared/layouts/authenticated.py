"""Authenticated page layout."""

import reflex as rx

from app.features.auth.components.forms import login_form
from app.features.chat.state import ChatState
from app.features.navigation.components.sidebars import navigation_sidebar


def authenticated_page(content: rx.Component, margin_left: str | None = "250px", margin_right: str | None = None):
    """Wrap content with authentication check and navigation.

    Args:
        content: The page content to wrap.
        margin_left: The left margin of the content.
        margin_right: The right margin of the content.

    Returns:
        A component with authentication and navigation.
    """

    return rx.cond(
        ChatState.is_authenticated,
        rx.box(
            navigation_sidebar(),
            rx.box(
                content,
                margin_left=margin_left,
                margin_right=margin_right,
            ),
        ),
        login_form(),
    )
