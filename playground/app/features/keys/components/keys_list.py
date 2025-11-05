"""API keys list component."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    ICON_SIZE_EMPTY_STATE,
    PADDING_PAGE,
    SIZE_MEDIUM,
    SPACING_MEDIUM,
    SPACING_NONE,
    SPACING_SMALL,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_LARGE,
)
from app.features.keys.components.keys_item import keys_item
from app.features.keys.components.keys_pagination import keys_pagination
from app.features.keys.state import KeysState


def keys_sorting() -> rx.Component:
    """Sorting controls for keys."""
    return rx.hstack(
        rx.text("Sort by", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select(
            ["id", "name", "created_at"],
            value=KeysState.keys_order_by,
            on_change=KeysState.set_keys_order_by,
        ),
        rx.select(
            ["asc", "desc"],
            value=KeysState.keys_order_direction,
            on_change=KeysState.set_keys_order_direction,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def keys_list() -> rx.Component:
    """Display list of API keys."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Your API keys", size=HEADING_SIZE_SECTION),
                rx.badge(
                    KeysState.keys.length(),
                    variant="soft",
                    color_scheme="blue",
                ),
                rx.spacer(),
                keys_sorting(),
                align="center",
                spacing=SPACING_SMALL,
                width="100%",
            ),
            rx.divider(),
            rx.cond(
                KeysState.keys_loading,
                rx.center(
                    rx.spinner(size=SIZE_MEDIUM),
                    width="100%",
                    padding=PADDING_PAGE,
                ),
                rx.cond(
                    KeysState.keys.length() > 0,
                    rx.vstack(
                        rx.foreach(KeysState.keys_with_formatted_dates, keys_item),
                        spacing=SPACING_NONE,
                        width="100%",
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon("key", size=ICON_SIZE_EMPTY_STATE, color=rx.color("mauve", 8)),
                            rx.text(
                                "No API keys yet",
                                size=TEXT_SIZE_LARGE,
                                color=rx.color("mauve", 10),
                            ),
                            rx.text(
                                "Create your first API key to get started",
                                size=TEXT_SIZE_LABEL,
                                color=rx.color("mauve", 9),
                            ),
                            spacing=SPACING_SMALL,
                        ),
                        width="100%",
                        padding=PADDING_PAGE,
                    ),
                ),
            ),
            rx.cond(
                KeysState.keys.length() > 0,
                rx.hstack(
                    keys_pagination(),
                    width="100%",
                    justify="end",
                ),
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )
