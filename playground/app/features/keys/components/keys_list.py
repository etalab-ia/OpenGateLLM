"""API keys list component."""

import reflex as rx

from app.features.keys.components.keys_item import keys_item
from app.features.keys.state import KeysState


def keys_list() -> rx.Component:
    """Display list of API keys."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Your API keys", size="6"),
                rx.badge(
                    KeysState.keys.length(),
                    variant="soft",
                    color_scheme="blue",
                ),
                align="center",
                spacing="2",
            ),
            rx.divider(),
            rx.cond(
                KeysState.keys_error != "",
                rx.callout(
                    KeysState.keys_error,
                    icon="triangle_alert",
                    color_scheme="red",
                ),
            ),
            rx.cond(
                KeysState.keys_loading,
                rx.center(
                    rx.spinner(size="3"),
                    width="100%",
                    padding="2em",
                ),
                rx.cond(
                    KeysState.keys.length() > 0,
                    rx.vstack(
                        rx.foreach(KeysState.keys_with_formatted_dates, keys_item),
                        spacing="0",
                        width="100%",
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon("key", size=48, color=rx.color("mauve", 8)),
                            rx.text(
                                "No API keys yet",
                                size="4",
                                color=rx.color("mauve", 10),
                            ),
                            rx.text(
                                "Create your first API key to get started",
                                size="2",
                                color=rx.color("mauve", 9),
                            ),
                            spacing="2",
                        ),
                        width="100%",
                        padding="2em",
                    ),
                ),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        max_width="1000px",
    )
