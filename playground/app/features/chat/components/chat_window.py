"""Chat window component for displaying conversation."""

import reflex as rx

from app.features.chat.components.message import message
from app.features.chat.state import ChatState


def chat() -> rx.Component:
    """List all the messages in a single conversation."""
    return rx.auto_scroll(
        rx.cond(
            ChatState.messages.length() > 0,
            rx.foreach(ChatState.messages, message),
            rx.center(
                rx.vstack(
                    rx.icon("message-square", size=48, color=rx.color("mauve", 8)),
                    rx.text(
                        "No messages yet",
                        size="4",
                        color=rx.color("mauve", 10),
                    ),
                    rx.text(
                        "Start a conversation by typing a message below",
                        size="2",
                        color=rx.color("mauve", 9),
                    ),
                    spacing="3",
                ),
                height="100%",
            ),
        ),
        flex="1",
        padding="16px",
    )
