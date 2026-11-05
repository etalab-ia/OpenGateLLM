"""Action bar component for sending messages."""

import reflex as rx

from app.features.chat.state import ChatState
from app.features.collections.models import Collection


def collection_option(collection: Collection) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=ChatState.selected_collection_ids.contains(collection.id),
            on_change=lambda _: ChatState.toggle_collection(collection.id),
            disabled=ChatState.processing,
            aria_label=collection.name,
        ),
        rx.text(collection.name, size="2", flex="1", overflow_wrap="anywhere"),
        spacing="2",
        align="center",
        width="100%",
    )


def collection_selector() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.switch(checked=ChatState.search_enabled, on_change=ChatState.set_search_enabled, disabled=ChatState.processing),
            rx.text("Search collections", size="2", weight="medium"),
            rx.spacer(),
            rx.link("Manage collections", href="/collections", size="1"),
            width="100%",
            align="center",
        ),
        rx.cond(
            ChatState.search_enabled,
            rx.vstack(
                rx.popover.root(
                    rx.popover.trigger(
                        rx.button(
                            rx.icon("folder-search", size=16),
                            rx.cond(
                                ChatState.selected_collection_count > 0,
                                f"{ChatState.selected_collection_count} selected",
                                "Select collections",
                            ),
                            variant="outline",
                            disabled=ChatState.processing,
                            width="100%",
                        ),
                    ),
                    rx.popover.content(
                        rx.cond(
                            ChatState.collections_loading,
                            rx.center(rx.spinner(size="2"), min_height="80px", width="100%"),
                            rx.cond(
                                ChatState.collections_error != "",
                                rx.vstack(
                                    rx.text(ChatState.collections_error, size="2", color=rx.color("red", 10)),
                                    rx.button("Try again", on_click=ChatState.load_collections, variant="soft", size="1"),
                                    spacing="2",
                                    align="start",
                                ),
                                rx.cond(
                                    ChatState.available_collections.length() > 0,
                                    rx.box(
                                        rx.vstack(rx.foreach(ChatState.available_collections, collection_option), spacing="3", align="start"),
                                        max_height="280px",
                                        overflow_y="auto",
                                        width="100%",
                                    ),
                                    rx.text("No collections available. Create one from Manage collections.", size="2", color=rx.color("mauve", 10)),
                                ),
                            ),
                        ),
                        width="360px",
                        max_width="90vw",
                        padding="16px",
                    ),
                ),
                rx.cond(
                    ChatState.selected_collection_count == 0,
                    rx.text("Select at least one collection to enable grounded chat.", size="1", color=rx.color("mauve", 10)),
                ),
                width="100%",
                spacing="2",
                align="stretch",
            ),
        ),
        width="100%",
        max_width="900px",
        margin="0 auto",
        spacing="2",
        align="stretch",
    )


def chat_input_bar() -> rx.Component:
    """The sidebar with sampling parameters."""
    return rx.box(
        rx.vstack(
            collection_selector(),
            rx.form(
                rx.hstack(
                    rx.input(
                        placeholder="Type your message...",
                        id="question",
                        flex="1",
                        disabled=ChatState.processing,
                    ),
                    rx.button(
                        rx.icon("send", size=18),
                        "Send",
                        loading=ChatState.processing,
                        disabled=ChatState.processing | (ChatState.search_enabled & (ChatState.selected_collection_count == 0)),
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
                "Models can make mistakes, please always verify sources and answers.",
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
        on_mount=ChatState.load_collections,
    )
