import reflex as rx

from app.core.configuration import configuration
from app.features.account.page import account_page
from app.features.auth.state import AuthState
from app.features.chat.page import chat_page_content
from app.features.keys.page import keys_page
from app.features.keys.state import KeysState
from app.features.organizations.page import organizations_page
from app.features.organizations.state import OrganizationsState
from app.features.providers.page import providers_page
from app.features.providers.state import ProvidersState
from app.features.roles.page import roles_page
from app.features.roles.state import RolesState
from app.features.routers.page import routers_page
from app.features.routers.state import RoutersState
from app.features.usage.page import usage_page
from app.features.usage.state import UsageState
from app.features.users.page import users_page
from app.features.users.state import UsersState
from app.shared.components.page import access_denied_page
from app.shared.layouts.authenticated import authenticated_page


def index() -> rx.Component:
    """Chat page."""
    return authenticated_page(chat_page_content())


def chat() -> rx.Component:
    """Chat page."""
    return authenticated_page(chat_page_content())


def account() -> rx.Component:
    """Account settings page."""
    return authenticated_page(
        rx.cond(
            ~AuthState.is_master,
            account_page(),
            access_denied_page(message="Master user cannot access this page."),
        )
    )


def keys() -> rx.Component:
    """API Keys management page."""
    return authenticated_page(
        rx.cond(
            ~AuthState.is_master,
            keys_page(),
            access_denied_page(message="Master user cannot access this page."),
        )
    )


def usage() -> rx.Component:
    """Usage page."""
    return authenticated_page(
        rx.cond(
            ~AuthState.is_master,
            usage_page(),
            access_denied_page(message="Master user cannot access this page."),
        )
    )


def roles() -> rx.Component:
    """Roles management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            roles_page(),
            access_denied_page(message="You need admin permissions to access this page."),
        )
    )


def users() -> rx.Component:
    """Users management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            users_page(),
            access_denied_page(message="You need admin permissions to access this page."),
        )
    )


def organizations() -> rx.Component:
    """Organizations management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            organizations_page(),
            access_denied_page(message="You need admin permissions to access this page."),
        )
    )


def routers() -> rx.Component:
    """Routers management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            routers_page(),
            access_denied_page(message="You need admin permissions to access this page."),
        )
    )


def providers() -> rx.Component:
    """Providers management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            providers_page(),
            access_denied_page(message="You need admin permissions to access this page."),
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
    head_components=[rx.el.link(rel="icon", type="image/svg+xml", href="/favicon.svg")],
)

# Add pages
app.add_page(component=index, route="/")
app.add_page(component=account, route="/account")
app.add_page(component=keys, route="/keys", on_load=[KeysState.load_entities])
app.add_page(component=usage, route="/usage", on_load=[UsageState.load_entities])
app.add_page(component=roles, route="/roles", on_load=[RolesState.load_entities])
app.add_page(component=users, route="/users", on_load=[UsersState.load_entities])
app.add_page(component=organizations, route="/organizations", on_load=[OrganizationsState.load_entities])
app.add_page(component=routers, route="/routers", on_load=[RoutersState.load_entities])
app.add_page(component=providers, route="/providers", on_load=[ProvidersState.load_entities])
