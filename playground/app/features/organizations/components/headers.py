import reflex as rx

from app.features.organizations.state import OrganizationsState
from app.shared.components.headers import entity_header


def organizations_header() -> rx.Component:
    """Organizations header."""
    return entity_header(title="Organizations management", state=OrganizationsState, admin_badge=True)
