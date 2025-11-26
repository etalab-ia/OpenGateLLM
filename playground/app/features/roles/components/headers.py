import reflex as rx

from app.features.roles.state import RolesState
from app.shared.components.headers import entity_header


def roles_header() -> rx.Component:
    """Roles header."""
    return entity_header(title="Roles management", state=RolesState, admin_badge=True)
