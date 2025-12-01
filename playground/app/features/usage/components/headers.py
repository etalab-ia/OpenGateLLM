"""Usage page header component."""

import reflex as rx

from app.features.usage.state import UsageState
from app.shared.components.headers import entity_header


def usage_header() -> rx.Component:
    """Usage header."""
    return entity_header(title="Usage", state=UsageState)
