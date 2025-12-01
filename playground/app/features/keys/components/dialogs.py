"""Dialog to display newly created API key."""

import reflex as rx

from app.core.variables import ICON_SIZE_MEDIUM, ICON_SIZE_XL, MAX_DIALOG_WIDTH, SIZE_MEDIUM, SPACING_LARGE, SPACING_SMALL, TEXT_SIZE_LABEL
from app.features.keys.state import KeysState
from app.shared.components.dialogs import entity_delete_dialog


def keys_created_dialog() -> rx.Component:
    """Dialog to display the newly created API key."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("check_check", size=ICON_SIZE_XL, color=rx.color("green", 11)),
                    "API Key created successfully!",
                    spacing=SPACING_SMALL,
                    align="center",
                )
            ),
            rx.dialog.description(
                "Copy your API key now. You won't be able to see it again!",
                color=rx.color("red", 11),
                weight="bold",
            ),
            rx.vstack(
                rx.vstack(
                    rx.text(
                        "Your API Key:",
                        size=TEXT_SIZE_LABEL,
                        weight="bold",
                        color=rx.color("mauve", 11),
                    ),
                    rx.text_area(
                        value=KeysState.created_key,
                        read_only=True,
                        width="100%",
                        min_height="120px",
                        size=SIZE_MEDIUM,
                    ),
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                rx.dialog.close(
                    rx.button(
                        rx.icon("check", size=ICON_SIZE_MEDIUM),
                        "I've copied the key",
                        on_click=KeysState.clear_created_key,
                        size=SIZE_MEDIUM,
                        width="100%",
                    ),
                ),
                spacing=SPACING_LARGE,
                width="100%",
            ),
            max_width=MAX_DIALOG_WIDTH,
        ),
        open=KeysState.is_created_dialog_open,
        on_open_change=KeysState.handle_created_dialog_change,
    )


def keys_delete_dialog() -> rx.Component:
    return entity_delete_dialog(
        state=KeysState,
        title="Delete key",
        description="Are you sure you want to delete this key? This action cannot be undone.",
    )
