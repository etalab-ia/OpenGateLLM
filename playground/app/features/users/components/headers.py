import reflex as rx

from app.features.users.state import UsersState
from app.shared.components.headers import entity_header


def users_header() -> rx.Component:
    """Roles header."""
    return entity_header(title="Users management", state=UsersState, admin_badge=True)
