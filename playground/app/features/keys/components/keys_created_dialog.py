"""Dialog to display newly created API key."""

import reflex as rx

from app.features.keys.state import KeysState


def keys_created_dialog() -> rx.Component:
    """Dialog to display the newly created API key."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("check_check", size=24, color=rx.color("green", 11)),
                    "API Key Created Successfully!",
                    spacing="2",
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
                        size="2",
                        weight="bold",
                        color=rx.color("mauve", 11),
                    ),
                    rx.text_area(
                        value=KeysState.created_key,
                        read_only=True,
                        width="100%",
                        min_height="120px",
                        size="3",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.callout(
                    "⚠️ Make sure to copy this key now. For security reasons, it won't be shown again.",
                    icon="shield-alert",
                    color_scheme="orange",
                    width="100%",
                ),
                rx.dialog.close(
                    rx.button(
                        rx.icon("check", size=18),
                        "I've copied the key",
                        on_click=KeysState.clear_created_key,
                        size="3",
                        width="100%",
                    ),
                ),
                spacing="4",
                width="100%",
            ),
            max_width="600px",
        ),
        open=KeysState.is_created_dialog_open,
        on_open_change=KeysState.handle_created_dialog_change,
    )
