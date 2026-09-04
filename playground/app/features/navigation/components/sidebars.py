import reflex as rx

from app.core.configuration import PlaygroundPages, configuration
from app.core.variables import PADDING_NAV
from app.features.auth.state import AuthState
from app.shared.components.dark_mode_toggle import dark_mode_toggle


def nav_admin_badge() -> rx.Component:
    return rx.badge("Admin", variant="soft", color_scheme="red", size="1")


def nav_item(label: str, icon: str | None, page: str, is_external: bool = False, admin: bool = False) -> rx.Component:
    """Navigation item.

    Args:
        label: The label for the navigation item.
        icon: The icon name. If None, reserve the same width so the label still aligns.
        page: The page to navigate to.
        is_external: Open the link in a new tab.
        admin: Show a compact Admin badge next to the label.

    Returns:
        A navigation item component.
    """
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=20) if icon else rx.box(width="20px", min_width="20px", height="20px"),
            rx.text(label, size="3"),
            nav_admin_badge() if admin else rx.fragment(),
            padding=PADDING_NAV,
            border_radius="8px",
            color=rx.color("mauve", 11),
            _hover={
                "background_color": rx.color("mauve", 3),
            },
            width="100%",
            spacing="3",
            align="center",
        ),
        href=page,
        is_external=is_external,
        text_decoration="none",
        width="100%",
    )


def navigation_sidebar() -> rx.Component:
    """Left navigation sidebar."""
    user_items = [
        (PlaygroundPages.ACCOUNT, nav_item("Account", "user", "/account")),
        (PlaygroundPages.KEYS, nav_item("API Keys", "key", "/keys")),
        (PlaygroundPages.USAGE, nav_item("Usage", "chart_line", "/usage")),
    ]
    user_items = [item for page, item in user_items if page not in configuration.settings.playground_disabled_pages]

    model_pages = [
        (PlaygroundPages.ROUTERS, nav_item("Routers", None, "/routers")),
        (PlaygroundPages.PROVIDERS, nav_item("Providers", None, "/providers")),
    ]
    model_items = [item for page, item in model_pages if page not in configuration.settings.playground_disabled_pages]

    admin_items = [
        (PlaygroundPages.ORGANIZATIONS, nav_item("Organizations", "building", "/organizations", admin=True)),
        (PlaygroundPages.ROLES, nav_item("Roles", "shield", "/roles", admin=True)),
        (PlaygroundPages.USERS, nav_item("Users", "users", "/users", admin=True)),
    ]
    admin_items = [item for page, item in admin_items if page not in configuration.settings.playground_disabled_pages]

    docs_items = []
    if configuration.settings.playground_documentation_url:
        docs_items.append(nav_item("Documentation", "book-open", configuration.settings.playground_documentation_url, is_external=True))
    if configuration.settings.playground_reference_url:
        docs_items.append(nav_item("API reference", "file-text", configuration.settings.playground_reference_url, is_external=True))
    if configuration.settings.playground_swagger_url:
        docs_items.append(nav_item("Swagger", "code", configuration.settings.playground_swagger_url, is_external=True))

    return rx.box(
        rx.vstack(
            # Navigation items
            rx.vstack(
                rx.link(
                    rx.hstack(
                        rx.image(
                            src="/logo.svg",
                            width="32px",
                            height="32px",
                        ),
                        rx.heading(
                            configuration.settings.app_title,
                            size="6",
                            color=rx.color("accent", 11),
                        ),
                        align="center",
                        spacing="2",
                        padding_bottom="1.5em",
                    ),
                    href="/",
                    style={"textDecoration": "none"},
                    width="100%",
                ),
                nav_item("Playground", "message-square", "/"),
                *user_items,
                *(
                    [
                        rx.cond(
                            AuthState.is_admin,
                            rx.vstack(
                                *(
                                    [
                                        rx.hstack(
                                            rx.icon("network", size=20),
                                            rx.text(
                                                "Models",
                                                size="4",
                                                weight="bold",
                                                color=rx.color("mauve", 12),
                                            ),
                                            nav_admin_badge(),
                                            padding_x=PADDING_NAV,
                                            padding_top=PADDING_NAV,
                                            padding_bottom="0.2em",
                                            spacing="3",
                                            align="center",
                                            width="100%",
                                        ),
                                        *model_items,
                                    ]
                                    if model_items
                                    else []
                                ),
                                *admin_items,
                                spacing="0",
                                width="100%",
                            ),
                        ),
                    ]
                    if model_items or admin_items
                    else []
                ),
                *([rx.divider(), *docs_items] if docs_items else []),
                spacing="0",
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
                        on_click=rx.cond(
                            configuration.settings.auth_login_type == "oidc",
                            AuthState.oidc_logout,
                            AuthState.password_logout,
                        ),
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
        border_right=f"1px solid {rx.color('mauve', 3)}",
        position="fixed",
        left="0",
        top="0",
    )
