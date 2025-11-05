"""Organizations page header."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_PAGE,
    ICON_SIZE_MEDIUM,
    ICON_SIZE_SMALL,
    MARGIN_MEDIUM,
    SPACING_MEDIUM,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
)
from app.features.organizations.state import OrganizationsState


def organizations_header() -> rx.Component:
    """Header for the organizations page."""
    return rx.hstack(
        rx.hstack(
            rx.heading("Organizations management", size=HEADING_SIZE_PAGE),
            rx.badge(
                rx.hstack(
                    rx.icon("shield-check", size=ICON_SIZE_SMALL),
                    rx.text("Admin", size=TEXT_SIZE_LABEL),
                    spacing=SPACING_TINY,
                    align="center",
                ),
                color_scheme="red",
                variant="soft",
                size="3",
            ),
            align="center",
            spacing=SPACING_MEDIUM,
        ),
        rx.button(
            rx.icon("refresh-cw", size=ICON_SIZE_MEDIUM),
            "Refresh",
            on_click=OrganizationsState.load_organizations,
            variant="soft",
            loading=OrganizationsState.organizations_loading,
        ),
        justify="between",
        align="center",
        width="100%",
        margin_bottom=MARGIN_MEDIUM,
    )
