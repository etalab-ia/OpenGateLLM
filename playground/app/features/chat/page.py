"""Chat page composition."""

import reflex as rx

from app.features.chat.components.headers import chat_header
from app.features.chat.components.input_bar import chat_input_bar
from app.features.chat.components.sidebar import chat_params_sidebar
from app.features.chat.components.window import chat_window


def chat_page_content() -> rx.Component:
    return rx.vstack(
        chat_header(),
        chat_window(),
        chat_input_bar(),
        chat_params_sidebar(),
        background_color=rx.color("mauve", 1),
        color=rx.color("mauve", 12),
        height="100vh",
        align_items="stretch",
        spacing="0",
    )
