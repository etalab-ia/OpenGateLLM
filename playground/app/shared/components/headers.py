import reflex as rx

from app.core.variables import (
    HEADING_SIZE_PAGE,
    HEADING_WEIGHT,
    ICON_SIZE_MEDIUM,
    MARGIN_MEDIUM,
    PADDING_PAGE,
    SPACING_MEDIUM,
)


def header_heading(title: str) -> rx.Component:
    """Heading with title."""
    return rx.heading(title, size=HEADING_SIZE_PAGE, weight=HEADING_WEIGHT)


def header_divider(*, bleed: bool = True) -> rx.Component:
    """Solid horizontal rule under a page header.

    When `bleed` is True, the rule breaks out of page padding so it spans the
    full content pane (full-bleed).
    """
    style = {
        "width": f"calc(100% + 2 * {PADDING_PAGE})" if bleed else "100%",
        "margin_left": f"-{PADDING_PAGE}" if bleed else "0",
        "margin_right": f"-{PADDING_PAGE}" if bleed else "0",
        "border_bottom": f"1px solid {rx.color('mauve', 6)}",
    }
    return rx.box(**style)


def page_header(title_row: rx.Component, *, bleed: bool = True, margin_bottom: str = MARGIN_MEDIUM) -> rx.Component:
    """Page title row with a full-width solid divider underneath."""
    return rx.vstack(
        title_row,
        header_divider(bleed=bleed),
        spacing=SPACING_MEDIUM,
        width="100%",
        margin_bottom=margin_bottom,
    )


def entity_refresh_button(state: rx.State) -> rx.Component:
    """Icon-only refresh control for page headers."""
    return rx.tooltip(
        rx.button(
            rx.icon("refresh-cw", size=ICON_SIZE_MEDIUM, color="black"),
            on_click=state.load_entities,
            variant="ghost",
            loading=state.entities_loading,
        ),
        content="Refresh",
    )


def entity_header(title: str, state: rx.State) -> rx.Component:
    """Header with title and refresh button."""
    return page_header(
        rx.hstack(
            header_heading(title),
            entity_refresh_button(state),
            width="100%",
            justify="between",
            align="center",
        )
    )


def header(title: str) -> rx.Component:
    """Header with title."""
    return page_header(header_heading(title))
