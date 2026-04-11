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

import requests
from fastapi import Request, HTTPException

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

async def login_proconnect(self, postgres_session: AsyncSession, email: str) -> tuple[int, str]:
    """
    Login a user authenticated via ProConnect (OIDC) and return a refreshed playground token.
    The user must already exist in the database (no auto-provisioning).
    Raises UserNotFoundException (404) if the user has not been provisioned by an admin.

    Args:
        postgres_session(AsyncSession): Database session
        email(str): User email asserted by the OIDC provider (injected by oauth2-proxy via X-Auth-Request-Email header)

    Returns:
        Tuple containing the token ID and the playground token.
    """
    user = await self.get_user(postgres_session=postgres_session, email=email)
    if user is None:
        raise UserNotFoundException()

    token_id, token = await self.refresh_token(postgres_session, user_id=user.id, name=self.PLAYGROUND_KEY_NAME)
    return token_id, token

fastapi_app = FastAPI(title="My API")

# Add routes to the FastAPI app
@fastapi_app.get("/api/items")
async def get_items():
    return dict(items=["Item1", "Item2", "Item3"])

@fastapi_app.post(path="/oauth2/authorize")
async def login_proconnect(request: Request) -> LoginResponse:
    """
    Exchange ProConnect identity (injected by oauth2-proxy) for a playground API token.
    The user email is read from the X-Auth-Request-Email header set by oauth2-proxy after a successful OIDC authentication.
    The user must already exist in the database; no auto-provisioning is performed.
    """
    email = request.headers.get("X-Auth-Request-Email")
    if not email:
        raise HTTPException(status_code=401, detail="Missing ProConnect authentication headers.")

    token_id, token = await global_context.identity_access_manager.login_proconnect(postgres_session=postgres_session, email=email)

    return JSONResponse(status_code=200, content=LoginResponse(id=token_id, key=token).model_dump())

# Create the app with theme configuration
app = rx.App(
    stylesheets=["proconnect.css"],
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
    api_transformer=fastapi_app
)

# Add pages
app.add_page(component=index, route="/", on_load=[AuthState.login_proconnect])
app.add_page(component=account, route="/account")
app.add_page(component=keys, route="/keys", on_load=[KeysState.load_entities])
app.add_page(component=usage, route="/usage", on_load=[UsageState.load_entities])
app.add_page(component=roles, route="/roles", on_load=[RolesState.load_entities])
app.add_page(component=users, route="/users", on_load=[UsersState.load_entities])
app.add_page(component=organizations, route="/organizations", on_load=[OrganizationsState.load_entities])
app.add_page(component=routers, route="/routers", on_load=[RoutersState.load_entities])
app.add_page(component=providers, route="/providers", on_load=[ProvidersState.load_entities])
