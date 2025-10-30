"""Chat page composition."""

import reflex as rx

from app.features.chat.components import action_bar, chat
from app.features.navigation.components.navbar import navbar


def chat_page_content() -> rx.Component:
    return rx.vstack(
        navbar(),
        chat(),
        action_bar(),
        background_color=rx.color("mauve", 1),
        color=rx.color("mauve", 12),
        height="100vh",
        align_items="stretch",
        spacing="0",
    )
