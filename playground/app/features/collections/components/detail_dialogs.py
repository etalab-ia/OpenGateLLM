import reflex as rx

from app.features.collections.detail_state import (
    COLLECTION_UPLOAD_ID,
    MAX_DOCUMENT_SIZE,
    SUPPORTED_UPLOAD_TYPES,
    CollectionDetailState,
)
from app.features.collections.models import Chunk


def upload_document_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Upload documents"),
            rx.dialog.description("Files are parsed and indexed with the collection's default chunking settings."),
            rx.upload(
                rx.vstack(
                    rx.icon("cloud-upload", size=30, color=rx.color("accent", 10)),
                    rx.text("Choose files", weight="bold"),
                    rx.text("PDF, HTML, Markdown or TXT • 20 MB per file", size="2", color=rx.color("mauve", 10)),
                    spacing="2",
                    align="center",
                ),
                id=COLLECTION_UPLOAD_ID,
                accept=SUPPORTED_UPLOAD_TYPES,
                max_size=MAX_DOCUMENT_SIZE,
                multiple=True,
                disabled=CollectionDetailState.upload_loading,
                width="100%",
                padding="2em",
            ),
            rx.vstack(
                rx.foreach(rx.selected_files(COLLECTION_UPLOAD_ID), lambda filename: rx.text(filename, size="2", overflow_wrap="anywhere")),
                spacing="1",
                align="start",
                width="100%",
            ),
            rx.cond(
                CollectionDetailState.upload_status != "",
                rx.text(CollectionDetailState.upload_status, size="2", color=rx.color("mauve", 10)),
            ),
            rx.cond(
                CollectionDetailState.upload_error != "",
                rx.box(
                    rx.text(CollectionDetailState.upload_error, size="2", color=rx.color("red", 11), white_space="pre-line"),
                    padding="0.75em",
                    border_radius="6px",
                    background_color=rx.color("red", 3),
                    width="100%",
                    role="alert",
                ),
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button("Cancel", variant="soft", color_scheme="gray", disabled=CollectionDetailState.upload_loading),
                ),
                rx.cond(
                    rx.selected_files(COLLECTION_UPLOAD_ID).length() > 0,
                    rx.button(
                        "Clear",
                        variant="soft",
                        color_scheme="gray",
                        on_click=rx.clear_selected_files(COLLECTION_UPLOAD_ID),
                        disabled=CollectionDetailState.upload_loading,
                    ),
                ),
                rx.button(
                    "Upload and index",
                    on_click=CollectionDetailState.upload_documents(rx.upload_files(upload_id=COLLECTION_UPLOAD_ID)),
                    loading=CollectionDetailState.upload_loading,
                ),
                justify="end",
                spacing="3",
                width="100%",
                margin_top="1em",
                flex_wrap="wrap",
            ),
            max_width="560px",
        ),
        open=CollectionDetailState.is_upload_dialog_open,
        on_open_change=CollectionDetailState.handle_upload_dialog_change,
    )


def delete_document_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete document"),
            rx.alert_dialog.description("Delete this document and all of its indexed chunks? This action cannot be undone."),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button("Cancel", variant="soft", color_scheme="gray", disabled=CollectionDetailState.delete_entity_loading)
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Delete",
                        color_scheme="red",
                        on_click=CollectionDetailState.delete_document,
                        loading=CollectionDetailState.delete_entity_loading,
                    )
                ),
                justify="end",
                spacing="3",
                width="100%",
            ),
        ),
        open=CollectionDetailState.is_delete_document_dialog_open,
        on_open_change=CollectionDetailState.handle_delete_document_dialog_change,
    )


def chunk_card(chunk: Chunk) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.badge(f"Chunk {chunk.id}", variant="soft", color_scheme="gray"),
                rx.cond(
                    chunk.page_number.is_not_none(),
                    rx.badge(f"Page {chunk.page_number}", variant="soft", color_scheme="blue"),
                ),
                rx.spacer(),
                rx.text(chunk.created, size="1", color=rx.color("mauve", 9)),
                width="100%",
                align="center",
                flex_wrap="wrap",
                gap="2",
            ),
            rx.box(
                rx.text(chunk.content, size="2", white_space="pre-wrap", overflow_wrap="anywhere"),
                padding="0.75em",
                border_radius="6px",
                background_color=rx.color("mauve", 2),
                width="100%",
            ),
            rx.vstack(
                rx.text("Metadata", size="2", weight="bold"),
                rx.cond(
                    chunk.metadata_json == "{}",
                    rx.text("No metadata", size="2", color=rx.color("mauve", 9)),
                    rx.el.pre(
                        rx.el.code(chunk.metadata_json),
                        style={
                            "margin": "0",
                            "white_space": "pre-wrap",
                            "overflow_wrap": "anywhere",
                            "font_size": "0.8em",
                        },
                    ),
                ),
                spacing="1",
                align="start",
                width="100%",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        padding="1em",
        border=f"1px solid {rx.color('mauve', 5)}",
        border_radius="6px",
        width="100%",
    )


def chunk_inspector_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Chunk inspector"),
            rx.dialog.description(CollectionDetailState.selected_document.name),
            rx.cond(
                CollectionDetailState.chunks_loading,
                rx.center(rx.spinner(size="3"), min_height="240px", width="100%"),
                rx.cond(
                    CollectionDetailState.chunks_error != "",
                    rx.center(
                        rx.vstack(
                            rx.icon("circle-alert", size=32, color=rx.color("red", 9)),
                            rx.text(CollectionDetailState.chunks_error, text_align="center", color=rx.color("mauve", 10)),
                            rx.button("Try again", on_click=CollectionDetailState.load_chunks),
                            spacing="3",
                            align="center",
                        ),
                        min_height="240px",
                        width="100%",
                    ),
                    rx.cond(
                        CollectionDetailState.chunks.length() > 0,
                        rx.vstack(
                            rx.scroll_area(
                                rx.vstack(rx.foreach(CollectionDetailState.chunks, chunk_card), spacing="3", width="100%"),
                                max_height="55vh",
                                width="100%",
                            ),
                            rx.flex(
                                rx.text(f"Page {CollectionDetailState.chunk_page}", size="2", color=rx.color("mauve", 10)),
                                rx.spacer(),
                                rx.icon_button(
                                    "chevron-left",
                                    on_click=CollectionDetailState.previous_chunks_page,
                                    disabled=CollectionDetailState.chunk_page <= 1,
                                    aria_label="Previous chunks page",
                                ),
                                rx.icon_button(
                                    "chevron-right",
                                    on_click=CollectionDetailState.next_chunks_page,
                                    disabled=~CollectionDetailState.chunks_has_next_page,
                                    aria_label="Next chunks page",
                                ),
                                align="center",
                                width="100%",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        rx.center(rx.text("No chunks were returned for this document.", color=rx.color("mauve", 10)), min_height="240px"),
                    ),
                ),
            ),
            max_width="860px",
            width="calc(100vw - 2em)",
        ),
        open=CollectionDetailState.is_chunk_dialog_open,
        on_open_change=CollectionDetailState.handle_chunk_dialog_change,
    )
