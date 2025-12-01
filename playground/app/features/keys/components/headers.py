import reflex as rx

from app.features.keys.state import KeysState
from app.shared.components.headers import entity_header


def keys_header() -> rx.Component:
    """API keys header."""
    return entity_header(title="API keys", state=KeysState)
