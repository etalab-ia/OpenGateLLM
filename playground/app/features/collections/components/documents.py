import reflex as rx

from app.core.variables import SPACING_MEDIUM, SPACING_SMALL, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.collections.detail_state import CollectionDetailState
from app.features.collections.models import Document


def document_row(document: Document) -> rx.Component:
    return rx.box(
        rx.flex(
            rx.box(
                rx.icon("file-text", size=22, color=rx.color("accent", 10)),
                padding="0.6em",
                border_radius="6px",
                background_color=rx.color("accent", 3),
                flex_shrink="0",
            ),
            rx.vstack(
                rx.text(document.name, size=TEXT_SIZE_LARGE, weight="bold", overflow_wrap="anywhere"),
                rx.text(
                    document.chunks,
                    " ",
                    rx.cond(document.chunks == 1, "chunk", "chunks"),
                    f" • {document.size} tokens",
                    size=TEXT_SIZE_LABEL,
                    color=rx.color("mauve", 9),
                ),
                rx.text(f"Added {document.created}", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                spacing="1",
                align="start",
                min_width="0",
                flex="1",
            ),
            rx.hstack(
                rx.tooltip(
                    rx.icon_button(
                        "eye",
                        on_click=CollectionDetailState.open_chunk_inspector(document),
                        variant="ghost",
                        size="2",
                        aria_label="Inspect chunks",
                        title="Inspect chunks",
                    ),
                    content="Inspect chunks",
                ),
                rx.cond(
                    CollectionDetailState.detail_collection.is_owner,
                    rx.tooltip(
                        rx.icon_button(
                            "trash-2",
                            on_click=CollectionDetailState.set_document_to_delete(document),
                            variant="ghost",
                            color_scheme="red",
                            size="2",
                            aria_label="Delete document",
                            title="Delete document",
                        ),
                        content="Delete document",
                    ),
                ),
                spacing="1",
                flex_shrink="0",
            ),
            gap=SPACING_MEDIUM,
            align="center",
            width="100%",
        ),
        padding_y="1em",
        border_bottom=f"1px solid {rx.color('mauve', 5)}",
        width="100%",
    )


def document_list() -> rx.Component:
    return rx.cond(
        CollectionDetailState.documents_loading,
        rx.center(rx.spinner(size="3"), min_height="260px", width="100%"),
        rx.cond(
            CollectionDetailState.documents_error != "",
            rx.center(
                rx.vstack(
                    rx.icon("circle-alert", size=36, color=rx.color("red", 9)),
                    rx.heading("Unable to load documents", size="4"),
                    rx.text(CollectionDetailState.documents_error, text_align="center", color=rx.color("mauve", 10)),
                    rx.button("Try again", on_click=CollectionDetailState.load_documents),
                    spacing="3",
                    align="center",
                    max_width="420px",
                ),
                min_height="260px",
                width="100%",
            ),
            rx.cond(
                CollectionDetailState.documents.length() > 0,
                rx.vstack(
                    rx.box(
                        rx.foreach(CollectionDetailState.documents, document_row),
                        border_top=f"1px solid {rx.color('mauve', 5)}",
                        width="100%",
                    ),
                    rx.flex(
                        rx.text(f"Page {CollectionDetailState.document_page}", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 10)),
                        rx.spacer(),
                        rx.icon_button(
                            "chevron-left",
                            on_click=CollectionDetailState.previous_documents_page,
                            disabled=CollectionDetailState.document_page <= 1,
                            aria_label="Previous documents page",
                        ),
                        rx.icon_button(
                            "chevron-right",
                            on_click=CollectionDetailState.next_documents_page,
                            disabled=~CollectionDetailState.documents_has_next_page,
                            aria_label="Next documents page",
                        ),
                        align="center",
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("files", size=48, color=rx.color("mauve", 8)),
                        rx.heading("No documents yet", size="4"),
                        rx.text(
                            rx.cond(
                                CollectionDetailState.detail_collection.is_owner,
                                "Upload a PDF, HTML, Markdown or TXT file to build this collection.",
                                "This public collection has no documents.",
                            ),
                            color=rx.color("mauve", 10),
                            text_align="center",
                        ),
                        rx.cond(
                            CollectionDetailState.detail_collection.is_owner,
                            rx.button(rx.icon("upload", size=18), "Upload documents", on_click=CollectionDetailState.open_upload_dialog),
                        ),
                        spacing=SPACING_SMALL,
                        align="center",
                    ),
                    min_height="260px",
                    width="100%",
                ),
            ),
        ),
    )
