import reflex as rx

from app.core.configuration import configuration
from app.features.account.page import account_page
from app.features.account.state import AccountState
from app.features.chat.page import chat_page_content
from app.features.keys.page import keys_page
from app.features.keys.state import KeysState
from app.features.limits.page import limits_page
from app.features.usage.page import usage_page
from app.features.usage.state import UsageState
from app.shared.layouts.authenticated import authenticated_page


def index() -> rx.Component:
    """Chat page."""
    return authenticated_page(chat_page_content(), with_sidebar_params=True)


def account() -> rx.Component:
    """Account settings page."""
    return authenticated_page(account_page())


def keys() -> rx.Component:
    """API Keys management page."""
    return authenticated_page(keys_page())


def limits() -> rx.Component:
    """Rate limits page."""
    return authenticated_page(limits_page())


def usage() -> rx.Component:
    """Usage page."""
    return authenticated_page(usage_page())


# Create the app with theme configuration
app = rx.App(
    theme=rx.theme(
        has_background=configuration.playground.theme_has_background,
        accent_color=configuration.playground.theme_accent_color,
        appearance=configuration.playground.theme_appearance,
        gray_color=configuration.playground.theme_gray_color,
        panel_background=configuration.playground.theme_panel_background,
        radius=configuration.playground.theme_radius,
        scaling=configuration.playground.theme_scaling,
    ),
    head_components=[
        rx.el.link(rel="icon", type="image/x-icon", href="/favicon.ico"),
    ],
)

# Add pages
app.add_page(index, route="/")
app.add_page(account, route="/account", on_load=AccountState.clear_account_flash)
app.add_page(keys, route="/keys", on_load=KeysState.load_keys)
app.add_page(limits, route="/limits")
app.add_page(usage, route="/usage", on_load=UsageState.load_usage)
