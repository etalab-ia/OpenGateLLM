"""Chat page composition."""

import reflex as rx

from app.features.chat.components import chat, chat_input_bar, chat_params_sidebar
from app.features.chat.components.chat_header import chat_header


def chat_page_content() -> rx.Component:
    return rx.vstack(
        chat_header(),
        chat(),
        chat_input_bar(),
        chat_params_sidebar(),
        background_color=rx.color("mauve", 1),
        color=rx.color("mauve", 12),
        height="100vh",
        align_items="stretch",
        spacing="0",
    )
