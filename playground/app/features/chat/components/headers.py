"""Chat page header component."""

import reflex as rx

from app.core.variables import ICON_SIZE_XL, PADDING_MEDIUM, PADDING_PAGE
from app.features.chat.state import ChatState
from app.shared.components.headers import header_heading, page_header


def chat_header() -> rx.Component:
    """Full-width Playground title."""
    return page_header(
        rx.box(
            header_heading("Playground"),
            padding_x=PADDING_PAGE,
            padding_top=PADDING_PAGE,
            width="100%",
        ),
        bleed=False,
        margin_bottom="0",
    )


def new_chat_button() -> rx.Component:
    """Start a new conversation, shown under the page header."""
    return rx.hstack(
        rx.spacer(),
        rx.tooltip(
            rx.button(
                rx.icon(
                    "message-square-plus",
                    size=ICON_SIZE_XL,
                    color="black",
                ),
                on_click=ChatState.clear_chat,
                variant="ghost",
            ),
            content="New chat",
            side="bottom",
        ),
        padding_x=PADDING_PAGE,
        padding_y=PADDING_MEDIUM,
        width="100%",
        align="center",
    )
