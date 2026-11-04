import reflex as rx

from app.core.variables import ICON_SIZE_MEDIUM, SPACING_MEDIUM, SPACING_SMALL, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.collections.models import Collection
from app.features.collections.state import CollectionsState


def collection_filters() -> rx.Component:
    return rx.flex(
        rx.form(
            rx.hstack(
                rx.input(
                    rx.input.slot(rx.icon("search", size=16)),
                    placeholder="Search by exact name",
                    value=CollectionsState.search_input,
                    on_change=CollectionsState.set_search_input,
                    width="100%",
                ),
                rx.button("Search", type="submit", variant="soft"),
                rx.cond(
                    CollectionsState.search != "",
                    rx.icon_button(
                        "x",
                        on_click=CollectionsState.clear_search,
                        variant="ghost",
                        aria_label="Clear search",
                    ),
                ),
                spacing=SPACING_SMALL,
                width="100%",
            ),
            on_submit=CollectionsState.submit_search,
            flex="1 1 280px",
            min_width="0",
        ),
        rx.select(
            CollectionsState.visibility_options,
            value=CollectionsState.visibility_filter,
            on_change=CollectionsState.set_visibility_filter,
            width="120px",
            aria_label="Visibility",
        ),
        rx.select(
            CollectionsState.order_by_options,
            value=CollectionsState.order_by_value,
            on_change=CollectionsState.set_order_by,
            width="120px",
            aria_label="Sort by",
        ),
        rx.select(
            CollectionsState.order_direction_options,
            value=CollectionsState.order_direction_value,
            on_change=CollectionsState.set_order_direction,
            width="100px",
            aria_label="Sort direction",
        ),
        gap=SPACING_MEDIUM,
        align="center",
        wrap="wrap",
        width="100%",
    )


def collection_row(collection: Collection) -> rx.Component:
    return rx.box(
        rx.flex(
            rx.box(
                rx.icon("folder", size=24, color=rx.color("accent", 10)),
                padding="0.65em",
                border_radius="6px",
                background_color=rx.color("accent", 3),
                flex_shrink="0",
            ),
            rx.vstack(
                rx.hstack(
                    rx.link(
                        rx.text(collection.name, size=TEXT_SIZE_LARGE, weight="bold", overflow_wrap="anywhere"),
                        href=f"/collections/{collection.id}",
                        underline="hover",
                        color=rx.color("mauve", 12),
                    ),
                    rx.badge(collection.visibility, variant="soft", color_scheme=rx.cond(collection.visibility == "public", "green", "gray")),
                    spacing=SPACING_SMALL,
                    align="center",
                    flex_wrap="wrap",
                ),
                rx.cond(
                    collection.description != "",
                    rx.text(collection.description, size=TEXT_SIZE_LABEL, color=rx.color("mauve", 10), overflow_wrap="anywhere"),
                ),
                rx.text(
                    f"{collection.documents} documents • {collection.size} tokens • Updated {collection.updated}",
                    size=TEXT_SIZE_LABEL,
                    color=rx.color("mauve", 9),
                ),
                spacing="1",
                align="start",
                min_width="0",
                flex="1",
            ),
            rx.cond(
                collection.is_owner,
                rx.hstack(
                    rx.tooltip(
                        rx.icon_button(
                            "pencil",
                            on_click=lambda: CollectionsState.set_entity_settings(collection),
                            variant="ghost",
                            size="2",
                            aria_label="Edit collection",
                            title="Edit collection",
                        ),
                        content="Edit collection",
                    ),
                    rx.tooltip(
                        rx.icon_button(
                            "trash-2",
                            on_click=lambda: CollectionsState.set_entity_to_delete(collection),
                            variant="ghost",
                            color_scheme="red",
                            size="2",
                            aria_label="Delete collection",
                            title="Delete collection",
                        ),
                        content="Delete collection",
                    ),
                    spacing="1",
                    flex_shrink="0",
                ),
                rx.badge("Read only", variant="outline", color_scheme="gray", flex_shrink="0"),
            ),
            gap=SPACING_MEDIUM,
            align="center",
            width="100%",
        ),
        padding_y="1em",
        border_bottom=f"1px solid {rx.color('mauve', 5)}",
        width="100%",
    )


def collection_list() -> rx.Component:
    return rx.cond(
        CollectionsState.entities_loading,
        rx.center(rx.spinner(size="3"), min_height="300px", width="100%"),
        rx.cond(
            CollectionsState.load_error != "",
            rx.center(
                rx.vstack(
                    rx.icon("circle-alert", size=36, color=rx.color("red", 9)),
                    rx.heading("Unable to load collections", size="4"),
                    rx.text(CollectionsState.load_error, text_align="center", color=rx.color("mauve", 10)),
                    rx.button("Try again", on_click=CollectionsState.load_entities),
                    spacing="3",
                    align="center",
                    max_width="420px",
                ),
                min_height="300px",
                width="100%",
            ),
            rx.cond(
                CollectionsState.collections.length() > 0,
                rx.vstack(
                    rx.box(
                        rx.foreach(CollectionsState.collections, collection_row),
                        border_top=f"1px solid {rx.color('mauve', 5)}",
                        width="100%",
                    ),
                    rx.flex(
                        rx.text(f"Page {CollectionsState.page}", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 10)),
                        rx.spacer(),
                        rx.icon_button(
                            "chevron-left", on_click=CollectionsState.prev_page, disabled=CollectionsState.page <= 1, aria_label="Previous page"
                        ),
                        rx.icon_button(
                            "chevron-right", on_click=CollectionsState.next_page, disabled=~CollectionsState.has_next_page, aria_label="Next page"
                        ),
                        align="center",
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("folder-open", size=48, color=rx.color("mauve", 8)),
                        rx.heading("No collections found", size="4"),
                        rx.text(
                            rx.cond(
                                (CollectionsState.search != "") | (CollectionsState.visibility_filter != "all"),
                                "Try changing your search or filters.",
                                "Create a private collection to organize your documents.",
                            ),
                            color=rx.color("mauve", 10),
                            text_align="center",
                        ),
                        rx.button(rx.icon("plus", size=ICON_SIZE_MEDIUM), "New collection", on_click=CollectionsState.open_create_dialog),
                        spacing="3",
                        align="center",
                    ),
                    min_height="300px",
                    width="100%",
                ),
            ),
        ),
    )
