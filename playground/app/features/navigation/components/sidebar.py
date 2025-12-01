import reflex as rx

from app.core.configuration import configuration
from app.features.auth.state import AuthState
from app.shared.components.dark_mode_toggle import dark_mode_toggle


def nav_item(label: str, icon: str, page: str) -> rx.Component:
    """Navigation item.

    Args:
        label: The label for the navigation item.
        icon: The icon name.
        page: The page to navigate to.

    Returns:
        A navigation item component.
    """
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=20),
            rx.text(label, size="3"),
            padding="0.75em",
            border_radius="8px",
            color=rx.color("mauve", 11),
            _hover={
                "background_color": rx.color("mauve", 3),
            },
            width="100%",
            spacing="3",
        ),
        href=page,
        text_decoration="none",
        width="100%",
    )


def navigation_sidebar() -> rx.Component:
    """Left navigation sidebar."""
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.image(
                    src="/logo.svg",
                    width="32px",
                    height="32px",
                ),
                rx.heading(
                    configuration.settings.app_title,
                    size="5",
                    color=rx.color("accent", 11),
                ),
                width="100%",
                padding="1em",
                border_bottom=f"1px solid {rx.color("mauve", 3)}",
                align_items="center",
            ),
            # Navigation items
            rx.vstack(
                nav_item("Chat", "message-square", "/"),
                rx.cond(
                    ~AuthState.is_master,
                    rx.box(
                        nav_item("Account", "user", "/account"),
                        nav_item("API Keys", "key", "/keys"),
                        nav_item("Usage", "bar-chart-3", "/usage"),
                        width="100%",
                    ),
                ),
                rx.cond(
                    AuthState.is_admin,
                    rx.box(
                        rx.divider(),
                        nav_item("Routers", "network", "/routers"),
                        nav_item("Providers", "container", "/providers"),
                        nav_item("Roles", "shield", "/roles"),
                        nav_item("Organizations", "building", "/organizations"),
                        nav_item("Users", "users", "/users"),
                        width="100%",
                    ),
                ),
                spacing="2",
                width="100%",
                padding="1em",
            ),
            # User info and logout at the bottom
            rx.spacer(),
            rx.vstack(
                rx.divider(),
                # Dark mode toggle
                rx.box(
                    dark_mode_toggle(),
                    width="100%",
                    display="flex",
                    justify_content="center",
                ),
                rx.divider(),
                rx.vstack(
                    rx.hstack(
                        rx.icon("user", size=16),
                        rx.vstack(
                            rx.text(
                                AuthState.user_name,
                                size="2",
                                weight="bold",
                                color=rx.color("mauve", 12),
                            ),
                            rx.text(
                                AuthState.user_email,
                                size="1",
                                color=rx.color("mauve", 10),
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.button(
                        rx.icon("log-out", size=16),
                        "Logout",
                        on_click=AuthState.logout,
                        variant="soft",
                        color_scheme="red",
                        width="100%",
                        size="2",
                    ),
                    spacing="3",
                    width="100%",
                ),
                spacing="3",
                width="100%",
                padding="1em",
            ),
            spacing="0",
            height="100%",
            width="100%",
        ),
        width="250px",
        height="100vh",
        background_color=rx.color("mauve", 2),
        border_right=f"1px solid {rx.color("mauve", 3)}",
        position="fixed",
        left="0",
        top="0",
    )
