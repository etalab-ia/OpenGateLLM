"""Dialog to display newly created API key."""

import reflex as rx

from app.core.variables import (
    ICON_SIZE_MEDIUM,
    ICON_SIZE_XL,
    MAX_DIALOG_WIDTH,
    PADDING_MEDIUM,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_SMALL,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_MEDIUM,
)
from app.features.keys.state import KeysState
from app.shared.components.dialogs import entity_delete_dialog


def _api_key_panel() -> rx.Component:
    """Tinted, bordered panel displaying the key on a single, horizontally-scrollable line."""
    return rx.scroll_area(
        rx.text(
            KeysState.created_key,
            font_family="monospace",
            size=TEXT_SIZE_MEDIUM,
            white_space="nowrap",
            user_select="none",
        ),
        scrollbars="horizontal",
        type="auto",
        width="100%",
        padding=PADDING_MEDIUM,
        background_color=rx.color("mauve", 2),
        border=f"1px solid {rx.color('mauve', 6)}",
        border_radius="0.5rem",
    )


def keys_created_dialog() -> rx.Component:
    """Dialog to display the newly created API key."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.icon("circle_check", size=ICON_SIZE_XL, color=rx.color("green", 9)),
                    rx.vstack(
                        rx.dialog.title("API key created", margin="0"),
                        rx.dialog.description(
                            "Your new API key is ready to use.",
                            color=rx.color("mauve", 11),
                            size=TEXT_SIZE_LABEL,
                        ),
                        spacing=SPACING_TINY,
                        align="start",
                    ),
                    spacing=SPACING_MEDIUM,
                    align="center",
                    width="100%",
                ),
                # Warning
                rx.callout(
                    "Copy your key now, for security reasons you won't be able to see it again.",
                    icon="triangle_alert",
                    color_scheme="amber",
                    variant="surface",
                    size="1",
                    width="100%",
                ),
                # Key
                rx.vstack(
                    rx.text(
                        "Your API key",
                        size=TEXT_SIZE_LABEL,
                        weight="bold",
                        color=rx.color("mauve", 11),
                    ),
                    _api_key_panel(),
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                # Footer
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Done",
                            on_click=KeysState.clear_created_key,
                            variant="soft",
                            color_scheme="gray",
                            size=SIZE_MEDIUM,
                        ),
                    ),
                    rx.button(
                        rx.icon("copy", size=ICON_SIZE_MEDIUM),
                        "Copy API key",
                        on_click=[
                            rx.set_clipboard(KeysState.created_key),
                            rx.toast.success("API key copied to clipboard", position="bottom-right"),
                        ],
                        size=SIZE_MEDIUM,
                    ),
                    spacing=SPACING_MEDIUM,
                    justify="end",
                    width="100%",
                ),
                spacing=SPACING_LARGE,
                width="100%",
            ),
            max_width=MAX_DIALOG_WIDTH,
            padding=PADDING_MEDIUM,
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
