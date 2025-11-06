import reflex as rx

from app.core.configuration import configuration
from app.features.account.page import account_page
from app.features.auth.state import AuthState
from app.features.chat.page import chat_page_content
from app.features.keys.page import keys_page
from app.features.keys.state import KeysState
from app.features.organizations.page import organizations_page
from app.features.organizations.state import OrganizationsState
from app.features.roles.page import roles_page
from app.features.roles.state import RolesState
from app.features.usage.page import usage_page
from app.features.usage.state import UsageState
from app.features.users.page import users_page
from app.features.users.state import UsersState
from app.shared.layouts.authenticated import authenticated_page


def index() -> rx.Component:
    """Chat page."""
    return authenticated_page(chat_page_content(), margin_right="320px")


def chat() -> rx.Component:
    """Chat page."""
    return authenticated_page(chat_page_content(), margin_right="320px")


def account() -> rx.Component:
    """Account settings page."""
    return authenticated_page(
        rx.cond(
            ~AuthState.is_master,
            account_page(),
            rx.center(
                rx.vstack(
                    rx.icon("shield-alert", size=64, color=rx.color("red", 9)),
                    rx.heading("Access Denied", size="8"),
                    rx.text("Master user cannot access this page.", size="4"),
                    spacing="4",
                ),
                height="100vh",
            ),
        )
    )


def keys() -> rx.Component:
    """API Keys management page."""
    return authenticated_page(
        rx.cond(
            ~AuthState.is_master,
            keys_page(),
            rx.center(
                rx.vstack(
                    rx.icon("shield-alert", size=64, color=rx.color("red", 9)),
                    rx.heading("Access Denied", size="8"),
                    rx.text("Master user cannot access this page.", size="4"),
                    spacing="4",
                ),
                height="100vh",
            ),
        )
    )


def usage() -> rx.Component:
    """Usage page."""
    return authenticated_page(
        rx.cond(
            ~AuthState.is_master,
            usage_page(),
            rx.center(
                rx.vstack(
                    rx.icon("shield-alert", size=64, color=rx.color("red", 9)),
                    rx.heading("Access Denied", size="8"),
                    rx.text("Master user cannot access this page.", size="4"),
                    spacing="4",
                ),
                height="100vh",
            ),
        )
    )


def roles() -> rx.Component:
    """Roles management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            roles_page(),
            rx.center(
                rx.vstack(
                    rx.icon("shield-alert", size=64, color=rx.color("red", 9)),
                    rx.heading("Access Denied", size="8"),
                    rx.text("You need admin permissions to access this page.", size="4"),
                    spacing="4",
                ),
                height="100vh",
            ),
        )
    )


def users() -> rx.Component:
    """Users management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            users_page(),
            rx.center(
                rx.vstack(
                    rx.icon("shield-alert", size=64, color=rx.color("red", 9)),
                    rx.heading("Access Denied", size="8"),
                    rx.text("You need admin permissions to access this page.", size="4"),
                    spacing="4",
                ),
                height="100vh",
            ),
        )
    )


def organizations() -> rx.Component:
    """Organizations management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            organizations_page(),
            rx.center(
                rx.vstack(
                    rx.icon("shield-alert", size=64, color=rx.color("red", 9)),
                    rx.heading("Access Denied", size="8"),
                    rx.text("You need admin permissions to access this page.", size="4"),
                    spacing="4",
                ),
                height="100vh",
            ),
        )
    )


# Create the app with theme configuration
app = rx.App(
    theme=rx.theme(
        has_background=configuration.settings.playground_theme_has_background,
        accent_color=configuration.settings.playground_theme_accent_color,
        appearance=configuration.settings.playground_theme_appearance,
        gray_color=configuration.settings.playground_theme_gray_color,
        panel_background=configuration.settings.playground_theme_panel_background,
        radius=configuration.settings.playground_theme_radius,
        scaling=configuration.settings.playground_theme_scaling,
    ),
    head_components=[
        rx.el.link(rel="icon", type="image/x-icon", href="/favicon.ico"),
    ],
)

# Add pages
app.add_page(index, route="/")
app.add_page(account, route="/account")
app.add_page(keys, route="/keys", on_load=KeysState.load_keys)
app.add_page(usage, route="/usage", on_load=UsageState.load_usage)
app.add_page(roles, route="/roles", on_load=RolesState.load_roles)
app.add_page(users, route="/users", on_load=[UsersState.load_users, UsersState.load_roles, UsersState.load_organizations])
app.add_page(organizations, route="/organizations", on_load=OrganizationsState.load_organizations)
