import reflex as rx

from app.core.variables import (
    HEADING_SIZE_PAGE,
    HEADING_WEIGHT,
    ICON_SIZE_MEDIUM,
    MARGIN_MEDIUM,
)


def header_heading(title: str) -> rx.Component:
    """Heading with title."""
    return rx.heading(title, size=HEADING_SIZE_PAGE, weight=HEADING_WEIGHT)


def entity_refresh_button(state: rx.State) -> rx.Component:
    """Refresh button."""
    return rx.button(
        rx.icon("refresh-cw", size=ICON_SIZE_MEDIUM),
        "Refresh",
        on_click=state.load_entities,
        variant="soft",
        loading=state.entities_loading,
    )


def entity_header(title: str, state: rx.State) -> rx.Component:
    """Header with title and refresh button."""
    return rx.hstack(
        header_heading(title),
        entity_refresh_button(state),
        width="100%",
        justify="between",
        align="center",
        margin_bottom=MARGIN_MEDIUM,
    )


def header(title: str) -> rx.Component:
    """Header with title."""
    return header_heading(title)
