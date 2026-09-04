"""Chat page composition."""

import reflex as rx

from app.features.chat.components.headers import chat_header
from app.features.chat.components.input_bars import chat_input_bar
from app.features.chat.components.sidebars import chat_params_sidebar
from app.features.chat.components.windows import chat_window


def chat_page_content() -> rx.Component:
    # Overflow hidden so only chat_window scrolls
    main_area_height = "100vh"

    return rx.hstack(
        # Left column: column with sticky header, scrollable chat window, sticky input
        rx.box(
            rx.vstack(
                # Sticky chat header
                rx.box(
                    chat_header(),
                    position="sticky",
                    top="0",
                    z_index="docked",
                    width="100%",
                ),
                # Chat window: the ONLY scrollable area
                rx.box(
                    chat_window(),
                    flex="1",
                    overflow="auto",
                    width="100%",
                    min_height="0",
                    padding_bottom="80px",  # ensure content isn't hidden by sticky input
                ),
                # Sticky input bar at the bottom of the left column
                rx.box(
                    chat_input_bar(),
                    position="sticky",
                    bottom="0",
                    z_index="banner",
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
            padding="0",
            position="relative",
            overflow="hidden",
        ),
        # Right column: fixed width params sidebar (non-scrollable)
        rx.box(
            chat_params_sidebar(),
            width="320px",
            flex="none",
            height="100%",
            overflow="hidden",
        ),
        align_items="stretch",
        spacing="0",
        width="100%",
        height=main_area_height,
    )
