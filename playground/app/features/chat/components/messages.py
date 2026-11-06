"""Message component for displaying chat messages."""

import reflex as rx
from reflex.constants.colors import ColorType

from app.features.chat.models import QA, ChatSource


def chat_source(source: ChatSource) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("file-text", size=16, color=rx.color("accent", 10)),
                rx.text(source["document_name"], size="2", weight="medium", overflow_wrap="anywhere"),
                rx.cond(
                    source["page_number"].is_not_none(),
                    rx.badge(f"Page {source['page_number']}", variant="soft", color_scheme="blue"),
                ),
                spacing="2",
                align="center",
                flex_wrap="wrap",
            ),
            rx.cond(
                source["content"] != "",
                rx.text(source["content"], size="1", color=rx.color("mauve", 10), white_space="pre-wrap", overflow_wrap="anywhere"),
            ),
            spacing="2",
            align="start",
        ),
        width="100%",
        padding="12px",
        border=f"1px solid {rx.color('mauve', 5)}",
        border_radius="6px",
        background_color=rx.color("mauve", 2),
    )


def chat_provenance(qa: QA) -> rx.Component:
    return rx.box(
        rx.cond(
            qa["sources_returned"],
            rx.cond(
                qa["sources"].length() > 0,
                rx.vstack(
                    rx.text("Sources", size="2", weight="bold", color=rx.color("mauve", 11)),
                    rx.foreach(qa["sources"], chat_source),
                    width="100%",
                    spacing="2",
                    align="start",
                ),
                rx.hstack(
                    rx.icon("info", size=16, color=rx.color("mauve", 9)),
                    rx.text("No documents found in the selected collections.", size="2", color=rx.color("mauve", 10)),
                    spacing="2",
                    align="center",
                ),
            ),
        ),
        width="100%",
        margin_bottom="8px",
    )


def chat_message_content(text: str, color: ColorType) -> rx.Component:
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


def chat_message(qa: QA) -> rx.Component:
    """A single question/answer message.

    Args:
        qa: The question/answer pair.

    Returns:
        A component displaying the question/answer pair.
    """
    return rx.box(
        rx.box(
            chat_message_content(qa["question"], "mauve"),
            text_align="right",
            margin_bottom="8px",
        ),
        rx.box(
            chat_message_content(qa["answer"], "accent"),
            text_align="left",
            margin_bottom="8px",
        ),
        chat_provenance(qa),
        width="100%",
        margin_inline="auto",
    )
