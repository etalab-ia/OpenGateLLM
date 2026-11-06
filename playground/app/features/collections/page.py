import reflex as rx

from app.core.variables import HEADING_SIZE_PAGE, HEADING_WEIGHT, PADDING_PAGE, SPACING_LARGE, SPACING_MEDIUM
from app.features.collections.components.dialogs import collection_create_dialog, collection_delete_dialog, collection_settings_dialog
from app.features.collections.components.lists import collection_filters, collection_list
from app.features.collections.state import CollectionsState
from app.shared.components.headers import entity_refresh_button, header_divider


def collections_page() -> rx.Component:
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Collections", size=HEADING_SIZE_PAGE, weight=HEADING_WEIGHT),
                        rx.hstack(
                            entity_refresh_button(CollectionsState),
                            rx.button(
                                rx.icon("plus", size=18),
                                "New collection",
                                on_click=CollectionsState.open_create_dialog,
                            ),
                            spacing=SPACING_MEDIUM,
                            align="center",
                            flex_wrap="wrap",
                            justify="end",
                        ),
                        width="100%",
                        justify="between",
                        align="center",
                        gap=SPACING_MEDIUM,
                        flex_wrap="wrap",
                    ),
                    header_divider(),
                    spacing=SPACING_MEDIUM,
                    width="100%",
                ),
                collection_filters(),
                collection_list(),
                spacing=SPACING_LARGE,
                width="100%",
                max_width="1400px",
                margin="0 auto",
                padding=PADDING_PAGE,
            ),
            height="100%",
        ),
        collection_create_dialog(),
        collection_settings_dialog(),
        collection_delete_dialog(),
        flex="1",
        width="100%",
        height="auto",
        background_color=rx.color("mauve", 1),
    )
