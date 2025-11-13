"""Individual API key item component."""

import reflex as rx

from app.features.keys.models import FormattedApiKey
from app.features.keys.state import KeysState


def keys_item(key: FormattedApiKey) -> rx.Component:
    """Display a single API key item with divider."""
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.text(
                    key.name,
                    size="3",
                    weight="bold",
                    color=rx.color("mauve", 12),
                ),
                rx.hstack(
                    rx.text(
                        "Token:",
                        size="2",
                        weight="bold",
                        color=rx.color("mauve", 11),
                    ),
                    rx.code(
                        rx.cond(
                            key.token.length() > 40,
                            key.token[:40] + "...",
                            key.token,
                        ),
                        size="2",
                    ),
                    spacing="2",
                ),
                rx.text(
                    f"Created: {key.created} • Expires: {key.expires}",
                    size="1",
                    color=rx.color("mauve", 9),
                ),
                spacing="2",
                align_items="start",
                flex="1",
            ),
            rx.button(
                rx.icon("trash-2", size=18),
                on_click=lambda: KeysState.set_key_to_delete(key.id),
                variant="soft",
                color_scheme="red",
                size="2",
            ),
            width="100%",
            align="center",
            justify="between",
            padding_y="0.75em",
        ),
        rx.divider(),
        width="100%",
    )
