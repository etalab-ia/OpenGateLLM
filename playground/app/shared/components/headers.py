import reflex as rx

from app.core.variables import (
    HEADING_SIZE_PAGE,
    ICON_SIZE_MEDIUM,
    ICON_SIZE_SMALL,
    MARGIN_MEDIUM,
    SPACING_MEDIUM,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_LINK,
)


def header_heading(title: str) -> rx.Component:
    """Heading with title."""
    return rx.heading(title, size=HEADING_SIZE_PAGE)


def header_admin_badge() -> rx.Component:
    """Admin badge."""
    return rx.badge(
        rx.hstack(
            rx.icon("shield-check", size=ICON_SIZE_SMALL),
            rx.text("Admin", size=TEXT_SIZE_LABEL),
            spacing=SPACING_TINY,
            align="center",
        ),
        color_scheme="red",
        variant="soft",
        size="3",
    )


def entity_refresh_button(state: rx.State) -> rx.Component:
    """Refresh button."""
    return rx.button(
        rx.icon("refresh-cw", size=ICON_SIZE_MEDIUM),
        "Refresh",
        on_click=state.load_entities,
        variant="soft",
        loading=state.entities_loading,
    )


def entity_header(title: str, state: rx.State, admin_badge: bool = False) -> rx.Component:
    """Header with title and refresh button."""
    return rx.hstack(
        rx.hstack(
            header_heading(title),
            rx.cond(admin_badge, header_admin_badge()),
            align="center",
            spacing=SPACING_MEDIUM,
        ),
        entity_refresh_button(state),
        width="100%",
        justify="between",
        align="center",
        margin_bottom=MARGIN_MEDIUM,
    )


def header(title: str, admin_badge: bool = False) -> rx.Component:
    """Header with title."""
    return rx.hstack(
        rx.hstack(
            header_heading(title),
            rx.cond(admin_badge, header_admin_badge()),
            align="center",
            spacing=SPACING_MEDIUM,
        )
    )


def nav_header(documentation_url: str | None, swagger_url: str | None, reference_url: str | None):
    return rx.box(
        rx.hstack(
            rx.link(
                "Documentation",
                href=documentation_url,
                color=rx.color("accent", 9),
                size=TEXT_SIZE_LINK,
            )
            if documentation_url
            else rx.fragment(),
            rx.link(
                "API reference",
                href=reference_url,
                color=rx.color("accent", 9),
                size=TEXT_SIZE_LINK,
            )
            if reference_url
            else rx.fragment(),
            rx.link(
                "Swagger",
                href=swagger_url,
                color=rx.color("accent", 9),
                size=TEXT_SIZE_LINK,
            )
            if swagger_url
            else rx.fragment(),
            width="100%",
            padding="1.12em",
            border_bottom=f"1px solid {rx.color("mauve", 3)}",
            justify_content="end",
            align_items="center",
            spacing="6",
        ),
        width="100%",
        background_color=rx.color("mauve", 1),
    )
