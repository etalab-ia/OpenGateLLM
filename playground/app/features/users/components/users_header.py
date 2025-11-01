import reflex as rx

from app.core.variables import (
    HEADING_SIZE_PAGE,
    ICON_SIZE_SMALL,
    MARGIN_MEDIUM,
    SPACING_MEDIUM,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
)


def users_header() -> rx.Component:
    """Header for users management page."""
    return rx.hstack(
        rx.heading("Users management", size=HEADING_SIZE_PAGE),
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
        width="100%",
        margin_bottom=MARGIN_MEDIUM,
    )
