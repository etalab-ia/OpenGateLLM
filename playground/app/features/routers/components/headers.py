import reflex as rx

from app.features.routers.state import RoutersState
from app.shared.components.headers import entity_header


def routers_header() -> rx.Component:
    """Routers header."""
    return entity_header(title="Routers management", state=RoutersState, admin_badge=True)
