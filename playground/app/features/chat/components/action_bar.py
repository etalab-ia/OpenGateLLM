"""Action bar component for sending messages."""

import reflex as rx

from app.features.chat.state import ChatState


def action_bar() -> rx.Component:
    """The action bar to send a new message."""
    return rx.box(
        rx.vstack(
            rx.form(
                rx.hstack(
                    rx.input(
                        rx.input.slot(
                            rx.tooltip(
                                rx.icon("info", size=18),
                                content="Enter a question to get a response.",
                            )
                        ),
                        placeholder="Type your message...",
                        id="question",
                        flex="1",
                        disabled=ChatState.processing,
                    ),
                    rx.button(
                        rx.icon("send", size=18),
                        "Send",
                        loading=ChatState.processing,
                        disabled=ChatState.processing,
                        type="submit",
                    ),
                    width="100%",
                    max_width="900px",
                    margin="0 auto",
                    align_items="center",
                    spacing="2",
                ),
                reset_on_submit=True,
                on_submit=ChatState.process_question,
                width="100%",
            ),
            rx.text(
                "I can make mistakes, please always verify my sources and answers.",
                text_align="center",
                font_size=".75em",
                color=rx.color("mauve", 10),
            ),
            width="100%",
            padding_x="16px",
            align="stretch",
            spacing="2",
        ),
        position="sticky",
        bottom="0",
        left="0",
        padding_y="16px",
        backdrop_filter="auto",
        backdrop_blur="lg",
        border_top=f"1px solid {rx.color('mauve', 3)}",
        background_color=rx.color("mauve", 2),
        width="100%",
    )
