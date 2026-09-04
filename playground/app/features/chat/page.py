"""Chat page composition."""

import reflex as rx

from app.features.chat.components.headers import chat_header
from app.features.chat.components.input_bars import chat_input_bar
from app.features.chat.components.sidebars import chat_params_sidebar
from app.features.chat.components.windows import chat_window


def chat_page_content() -> rx.Component:
    """Playground layout: full-width header, then chat and params side by side."""
    return rx.vstack(
        rx.box(
            chat_header(),
            width="100%",
            flex="none",
            background_color=rx.color("mauve", 1),
        ),
        rx.hstack(
            rx.box(
                rx.vstack(
                    rx.box(
                        chat_window(),
                        flex="1",
                        overflow="auto",
                        width="100%",
                        min_height="0",
                        padding_bottom="80px",
                    ),
                    rx.box(
                        chat_input_bar(),
                        width="100%",
                        background_color=rx.color("mauve", 1),
                    ),
                    spacing="0",
                    align_items="stretch",
                    height="100%",
                ),
                background_color=rx.color("mauve", 1),
                color=rx.color("mauve", 12),
                flex="1",
                min_width="0",
                height="100%",
                overflow="hidden",
            ),
            rx.box(
                chat_params_sidebar(),
                width="320px",
                flex="none",
                height="100%",
                overflow="auto",
            ),
            spacing="0",
            align_items="stretch",
            width="100%",
            flex="1",
            min_height="0",
        ),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        background_color=rx.color("mauve", 1),
    )
