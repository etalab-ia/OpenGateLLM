import reflex as rx

from app.core.configuration import configuration
from app.features.sso_access.state import SsoAccessState
from app.shared.components.headers import entity_header


def sso_access_header() -> rx.Component:
    """SSO access header."""
    return entity_header(title="SSO Access", state=SsoAccessState, admin_badge=True)


def sso_inactive_banner() -> rx.Component:
    return rx.cond(
        configuration.settings.auth_login_type != "oidc",
        rx.callout(
            "SSO is not active on this instance, please check the configuration. You can still view and edit the access policy here; it will apply when SSO is enabled.",
            icon="info",
            color_scheme="blue",
            variant="surface",
            size="1",
            width="100%",
        ),
    )
