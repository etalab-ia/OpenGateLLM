"""Authenticated page layout."""

import reflex as rx

from app.features.auth.components.login_form import login_page
from app.features.chat.state import ChatState
from app.features.navigation.components.sidebar_nav import sidebar_nav
from app.features.navigation.components.sidebar_params import sidebar_params


def authenticated_page(content: rx.Component, with_sidebar_params: bool = False) -> rx.Component:
    """Wrap content with authentication check and navigation.

    Args:
        content: The page content to wrap.
        with_sidebar_params: Whether to include the right sidebar with parameters.

    Returns:
        A component with authentication and navigation.
    """

    def page_content():
        if with_sidebar_params:
            return rx.box(
                sidebar_nav(),
                rx.box(
                    content,
                    margin_left="250px",
                    margin_right="320px",
                ),
                sidebar_params(),
            )
        else:
            return rx.box(
                sidebar_nav(),
                rx.box(
                    content,
                    margin_left="250px",
                ),
            )

    return rx.cond(
        ChatState.is_authenticated,
        page_content(),
        login_page(),
    )
