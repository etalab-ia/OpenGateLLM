import reflex as rx

from app.core.configuration import PlaygroundPages, configuration
from app.features.account.page import account_page
from app.features.auth.page import admin_deny_page, sso_deny_page, sso_error_page
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
from app.shared.layouts.authenticated import authenticated_page


def index() -> rx.Component:
    """Chat page."""
    return authenticated_page(chat_page_content())


def chat() -> rx.Component:
    """Chat page."""
    return authenticated_page(chat_page_content())


def account() -> rx.Component:
    """Account settings page."""
    return authenticated_page(account_page())


def keys() -> rx.Component:
    """API Keys management page."""
    return authenticated_page(keys_page())


def usage() -> rx.Component:
    """Usage page."""
    return authenticated_page(usage_page())


def roles() -> rx.Component:
    """Roles management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            roles_page(),
            admin_deny_page(),
        )
    )


def users() -> rx.Component:
    """Users management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            users_page(),
            admin_deny_page(),
        )
    )


def organizations() -> rx.Component:
    """Organizations management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            organizations_page(),
            admin_deny_page(),
        )
    )


def routers() -> rx.Component:
    """Routers management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            routers_page(),
            admin_deny_page(),
        )
    )


def providers() -> rx.Component:
    """Providers management page (admin only)."""
    return authenticated_page(
        rx.cond(
            AuthState.is_admin,
            providers_page(),
            admin_deny_page(),
        )
    )


app = rx.App(
    style={rx.heading: {"font_weight": "500"}},
    theme=rx.theme(
        has_background=configuration.settings.playground_theme_has_background,
        accent_color=configuration.settings.playground_theme_accent_color,
        appearance=configuration.settings.playground_theme_appearance,
        gray_color=configuration.settings.playground_theme_gray_color,
        panel_background=configuration.settings.playground_theme_panel_background,
        radius=configuration.settings.playground_theme_radius,
        scaling="90%",
    ),
    head_components=[rx.el.link(rel="icon", type="image/svg+xml", href="/favicon.svg")],
)


def _on_load(*handlers):
    login = AuthState.oidc_login if configuration.settings.auth_login_type == "oidc" else AuthState.ensure_session
    return [login, *handlers]


# Public pages
app.add_page(component=index, route="/", on_load=_on_load())
if configuration.settings.auth_login_type == "oidc":
    app.add_page(component=sso_deny_page, route="/deny")
    app.add_page(component=sso_error_page, route="/error")
if PlaygroundPages.ACCOUNT not in configuration.settings.playground_disabled_pages:
    app.add_page(component=account, route="/account", on_load=_on_load())
if PlaygroundPages.KEYS not in configuration.settings.playground_disabled_pages:
    app.add_page(component=keys, route="/keys", on_load=_on_load(KeysState.load_entities))
if PlaygroundPages.USAGE not in configuration.settings.playground_disabled_pages:
    app.add_page(component=usage, route="/usage", on_load=_on_load(UsageState.load_entities))

# Admin pages
if PlaygroundPages.ORGANIZATIONS not in configuration.settings.playground_disabled_pages:
    app.add_page(component=organizations, route="/organizations", on_load=_on_load(OrganizationsState.load_entities))
if PlaygroundPages.PROVIDERS not in configuration.settings.playground_disabled_pages:
    app.add_page(component=providers, route="/providers", on_load=_on_load(ProvidersState.load_entities))
if PlaygroundPages.ROLES not in configuration.settings.playground_disabled_pages:
    app.add_page(component=roles, route="/roles", on_load=_on_load(RolesState.load_entities))
if PlaygroundPages.ROUTERS not in configuration.settings.playground_disabled_pages:
    app.add_page(component=routers, route="/routers", on_load=_on_load(RoutersState.load_entities))
if PlaygroundPages.USERS not in configuration.settings.playground_disabled_pages:
    app.add_page(component=users, route="/users", on_load=_on_load(UsersState.load_entities))
