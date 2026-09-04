"""Chat page header component."""

import reflex as rx

from app.core.variables import ICON_SIZE_MEDIUM, MARGIN_MEDIUM, PADDING_PAGE
from app.features.chat.state import ChatState
from app.shared.components.headers import header_heading


def chat_header() -> rx.Component:
    """Page title and new-chat action, matching other feature headers."""
    return rx.hstack(
        header_heading("Playground"),
        rx.button(
            rx.icon("message-square-plus", size=ICON_SIZE_MEDIUM),
            "New chat",
            on_click=ChatState.clear_chat,
            variant="soft",
        ),
        width="100%",
        justify="between",
        align="center",
        margin_bottom=MARGIN_MEDIUM,
        padding_x=PADDING_PAGE,
        padding_top=PADDING_PAGE,
    )
