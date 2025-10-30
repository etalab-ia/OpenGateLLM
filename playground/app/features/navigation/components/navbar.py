"""Top navigation bar component."""

import reflex as rx

from app.features.chat.state import ChatState


def sidebar_chat(chat: str) -> rx.Component:
    """A sidebar chat item.

    Args:
        chat: The chat item.
    """
    return rx.drawer.close(
        rx.hstack(
            rx.button(
                chat,
                on_click=lambda: ChatState.set_chat(chat),
                width="80%",
                variant="surface",
            ),
            rx.button(
                rx.icon(
                    tag="trash",
                    on_click=ChatState.delete_chat(chat),
                    stroke_width=1,
                ),
                width="20%",
                variant="surface",
                color_scheme="red",
            ),
            width="100%",
        ),
        key=chat,
    )


def sidebar(trigger) -> rx.Component:
    """The sidebar component for chat history."""
    return rx.drawer.root(
        rx.drawer.trigger(trigger),
        rx.drawer.overlay(),
        rx.drawer.portal(
            rx.drawer.content(
                rx.vstack(
                    rx.heading("Chats", color=rx.color("mauve", 11)),
                    rx.divider(),
                    rx.foreach(ChatState.chat_titles, lambda chat: sidebar_chat(chat)),
                    align_items="stretch",
                    width="100%",
                ),
                top="auto",
                right="auto",
                height="100%",
                width="20em",
                padding="2em",
                background_color=rx.color("mauve", 2),
                outline="none",
            )
        ),
        direction="left",
    )


def modal(trigger) -> rx.Component:
    """A modal to create a new chat."""
    return rx.dialog.root(
        rx.dialog.trigger(trigger),
        rx.dialog.content(
            rx.form(
                rx.hstack(
                    rx.input(
                        placeholder="Chat name",
                        name="new_chat_name",
                        flex="1",
                        min_width="20ch",
                    ),
                    rx.button("Create chat"),
                    spacing="2",
                    wrap="wrap",
                    width="100%",
                ),
                on_submit=ChatState.create_chat,
            ),
            background_color=rx.color("mauve", 1),
        ),
        open=ChatState.is_modal_open,
        on_open_change=ChatState.set_is_modal_open,
    )


def navbar():
    """Top navbar with current chat and actions."""
    return rx.hstack(
        rx.badge(
            ChatState.current_chat,
            rx.tooltip(
                rx.icon("info", size=14),
                content="The current selected chat.",
            ),
            size="3",
            variant="soft",
            margin_inline_end="auto",
        ),
        modal(
            rx.icon_button("message-square-plus"),
        ),
        sidebar(
            rx.icon_button(
                "messages-square",
                background_color=rx.color("mauve", 6),
            )
        ),
        justify_content="space-between",
        align_items="center",
        padding="12px",
        border_bottom=f"1px solid {rx.color('mauve', 3)}",
        background_color=rx.color("mauve", 2),
    )
