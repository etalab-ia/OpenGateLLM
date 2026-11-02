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
            rx.drawer.root(
                rx.drawer.trigger(
                    rx.box(
                        rx.icon_button(
                            "menu",
                            variant="soft",
                            aria_label="Open navigation",
                        ),
                        position="fixed",
                        top="0.75em",
                        left="0.75em",
                        z_index="10",
                        display=rx.breakpoints(initial="block", lg="none"),
                    )
                ),
                rx.drawer.overlay(),
                rx.drawer.portal(
                    rx.drawer.content(
                        navigation_sidebar(drawer=True),
                        padding="0",
                        width="250px",
                        height="100vh",
                    )
                ),
                direction="left",
                modal=True,
            ),
            rx.box(
                content,
                width="100%",
                height="100vh",
                overflow="auto",
                padding_left=rx.breakpoints(initial="0px", lg=margin_left or "0px"),
                padding_right=margin_right or "0px",
            ),
            display="flex",
        ),
        rx.cond(
            AuthState.login_type == "oidc",
            login_card(login_form=oidc_login_form()),
            login_card(login_form=password_login_form()),
        ),
    )
