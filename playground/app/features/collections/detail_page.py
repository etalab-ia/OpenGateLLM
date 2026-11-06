import reflex as rx

from app.core.variables import HEADING_SIZE_PAGE, HEADING_WEIGHT, PADDING_PAGE, SPACING_LARGE, SPACING_MEDIUM
from app.features.collections.components.detail_dialogs import chunk_inspector_dialog, delete_document_dialog, upload_document_dialog
from app.features.collections.components.documents import document_list
from app.features.collections.detail_state import CollectionDetailState
from app.shared.components.headers import header_divider


def collection_detail_header() -> rx.Component:
    return rx.vstack(
        rx.flex(
            rx.vstack(
                rx.hstack(
                    rx.link("Collections", href="/collections", color=rx.color("accent", 10), underline="hover"),
                    rx.icon("chevron-right", size=14, color=rx.color("mauve", 9)),
                    rx.text(CollectionDetailState.detail_collection.name, size="2", color=rx.color("mauve", 10), overflow_wrap="anywhere"),
                    spacing="2",
                    align="center",
                    flex_wrap="wrap",
                ),
                rx.heading(CollectionDetailState.detail_collection.name, size=HEADING_SIZE_PAGE, weight=HEADING_WEIGHT, overflow_wrap="anywhere"),
                rx.hstack(
                    rx.badge(
                        CollectionDetailState.detail_collection.visibility,
                        variant="soft",
                        color_scheme=rx.cond(CollectionDetailState.detail_collection.visibility == "public", "green", "gray"),
                    ),
                    rx.cond(
                        ~CollectionDetailState.detail_collection.is_owner,
                        rx.badge("Read only", variant="outline", color_scheme="gray"),
                    ),
                    rx.text(
                        CollectionDetailState.detail_collection.documents,
                        " ",
                        rx.cond(CollectionDetailState.detail_collection.documents == 1, "document", "documents"),
                        f" • {CollectionDetailState.detail_collection.size} tokens",
                        size="2",
                        color=rx.color("mauve", 9),
                    ),
                    spacing="2",
                    align="center",
                    flex_wrap="wrap",
                ),
                rx.cond(
                    CollectionDetailState.detail_collection.description != "",
                    rx.text(CollectionDetailState.detail_collection.description, color=rx.color("mauve", 10), overflow_wrap="anywhere"),
                ),
                spacing="2",
                align="start",
                min_width="0",
                flex="1",
                width=rx.breakpoints(initial="100%", md="auto"),
            ),
            rx.hstack(
                rx.tooltip(
                    rx.button(
                        rx.icon("refresh-cw", size=18),
                        on_click=CollectionDetailState.refresh_collection_detail,
                        variant="ghost",
                        loading=CollectionDetailState.detail_loading,
                        aria_label="Refresh collection",
                        title="Refresh collection",
                    ),
                    content="Refresh collection",
                ),
                rx.cond(
                    CollectionDetailState.detail_collection.is_owner,
                    rx.button(rx.icon("upload", size=18), "Upload documents", on_click=CollectionDetailState.open_upload_dialog),
                ),
                spacing=SPACING_MEDIUM,
                align="center",
                flex_wrap="wrap",
                justify=rx.breakpoints(initial="start", md="end"),
                width=rx.breakpoints(initial="100%", md="auto"),
            ),
            width="100%",
            justify="between",
            align="start",
            gap=SPACING_MEDIUM,
            direction=rx.breakpoints(initial="column", md="row"),
        ),
        header_divider(),
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def collection_detail_content() -> rx.Component:
    return rx.vstack(
        collection_detail_header(),
        rx.heading("Documents", size="5", weight="medium"),
        document_list(),
        spacing=SPACING_LARGE,
        width="100%",
    )


def collection_detail_page() -> rx.Component:
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                rx.cond(
                    CollectionDetailState.detail_loading,
                    rx.center(rx.spinner(size="3"), min_height="360px", width="100%"),
                    rx.cond(
                        CollectionDetailState.detail_error != "",
                        rx.center(
                            rx.vstack(
                                rx.icon("circle-alert", size=40, color=rx.color("red", 9)),
                                rx.heading("Unable to load collection", size="4"),
                                rx.text(CollectionDetailState.detail_error, text_align="center", color=rx.color("mauve", 10)),
                                rx.link(rx.button("Back to collections", variant="soft"), href="/collections"),
                                spacing="3",
                                align="center",
                                max_width="440px",
                            ),
                            min_height="360px",
                            width="100%",
                        ),
                        rx.cond(
                            CollectionDetailState.detail_collection.id.is_not_none(),
                            collection_detail_content(),
                        ),
                    ),
                ),
                width="100%",
                max_width="1400px",
                min_height="100%",
                margin="0 auto",
                padding=PADDING_PAGE,
            ),
            height="100%",
        ),
        upload_document_dialog(),
        delete_document_dialog(),
        chunk_inspector_dialog(),
        flex="1",
        width="100%",
        height="auto",
        background_color=rx.color("mauve", 1),
    )
