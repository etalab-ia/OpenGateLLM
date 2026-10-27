"""Limits page header component."""

import reflex as rx

from app.features.limits.state import LimitsState
from app.shared.components.headers import entity_header


def limits_header() -> rx.Component:
    """Limits header."""
    return entity_header(title="Limits", state=LimitsState)
