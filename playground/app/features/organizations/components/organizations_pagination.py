"""Organizations pagination component."""

import reflex as rx

from app.core.variables import SIZE_MEDIUM, SPACING_SMALL, TEXT_SIZE_LABEL
from app.features.organizations.state import OrganizationsState


def organizations_pagination() -> rx.Component:
    """Pagination controls for organizations."""
    return rx.hstack(
        rx.button(
            "Prev",
            on_click=OrganizationsState.previous_organizations_page,
            disabled=~OrganizationsState.has_previous_organizations_page,
            size=SIZE_MEDIUM,
        ),
        rx.text(
            f"Page {OrganizationsState.organizations_page} / {OrganizationsState.organizations_total_pages}",
            size=TEXT_SIZE_LABEL,
        ),
        rx.button(
            "Next",
            on_click=OrganizationsState.next_organizations_page,
            disabled=~OrganizationsState.has_next_organizations_page,
            size=SIZE_MEDIUM,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )
