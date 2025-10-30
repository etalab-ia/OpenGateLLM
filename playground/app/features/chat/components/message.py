"""Message component for displaying chat messages."""

import reflex as rx
from reflex.constants.colors import ColorType

from app.features.chat.models import QA


def message_content(text: str, color: ColorType) -> rx.Component:
    """Create a message content component.

    Args:
        text: The text to display.
        color: The color of the message.

    Returns:
        A component displaying the message.
    """
    return rx.markdown(
        text,
        background_color=rx.color(color, 4),
        color=rx.color(color, 12),
        display="inline-block",
        padding_inline="1em",
        padding_block="0.5em",
        border_radius="8px",
        max_width="100%",
    )


def message(qa: QA) -> rx.Component:
    """A single question/answer message.

    Args:
        qa: The question/answer pair.

    Returns:
        A component displaying the question/answer pair.
    """
    return rx.box(
        rx.box(
            message_content(qa["question"], "mauve"),
            text_align="right",
            margin_bottom="8px",
        ),
        rx.box(
            message_content(qa["answer"], "accent"),
            text_align="left",
            margin_bottom="8px",
        ),
        width="100%",
        margin_inline="auto",
    )
