import reflex as rx

from app.features.providers.state import ProvidersState
from app.shared.components.headers import entity_header


def providers_header() -> rx.Component:
    """Providers header."""
    return entity_header(title="Providers management", state=ProvidersState, admin_badge=True)
