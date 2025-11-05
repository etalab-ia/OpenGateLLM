"""Chat page header component."""

import reflex as rx

from app.core.variables import ICON_SIZE_MEDIUM
from app.features.chat.state import ChatState


def chat_header() -> rx.Component:
    """Top navigation bar with title and refresh button."""
    return rx.hstack(
        rx.button(
            rx.icon("message-square-plus", size=ICON_SIZE_MEDIUM),
            "New chat",
            on_click=ChatState.clear_chat,
            variant="soft",
            margin_left="auto",
        ),
        width="100%",
        align_items="center",
        padding="12px",
        border_bottom=f"1px solid {rx.color("mauve", 3)}",
        background_color=rx.color("mauve", 2),
    )
