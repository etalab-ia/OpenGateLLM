from collections.abc import Callable

from pydantic import BaseModel
import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    ICON_SIZE_EMPTY_STATE,
    ICON_SIZE_MEDIUM,
    PADDING_PAGE,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_NONE,
    SPACING_SMALL,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_LARGE,
)


def entity_row(
    entity: BaseModel,
    state: rx.State,
    row_content: rx.Component,
    row_description: rx.Component,
    with_settings: bool = False,
) -> rx.Component:
    """Display a single entity item with update and delete buttons."""
    return rx.box(
        rx.hstack(
            rx.vstack(
                row_content,
                row_description,
                spacing=SPACING_SMALL,
                align_items="start",
                flex="1",
            ),
            rx.hstack(
                rx.cond(
                    with_settings,
                    rx.button(
                        rx.icon("settings", size=ICON_SIZE_MEDIUM),
                        on_click=lambda: state.set_entity_settings(entity=entity),
                        variant="soft",
                        color_scheme="blue",
                        size=TEXT_SIZE_LABEL,
                    ),
                ),
                rx.button(
                    rx.icon("trash-2", size=ICON_SIZE_MEDIUM),
                    on_click=lambda: state.set_entity_to_delete(entity=entity),
                    variant="soft",
                    color_scheme="red",
                    size=TEXT_SIZE_LABEL,
                    disabled=state.delete_entity_loading,
                    loading=state.delete_entity_loading,
                ),
                spacing=SPACING_SMALL,
            ),
            width="100%",
            align="center",
            justify="between",
            padding_y="0.75em",
        ),
        rx.divider(),
        width="100%",
    )


def entity_pagination(state: rx.State) -> rx.Component:
    """Pagination controls for entity list."""
    return rx.hstack(
        rx.button(
            "Prev",
            on_click=state.prev_page,
            disabled=state.page <= 1,
        ),
        rx.text(
            state.page.to(str),
        ),
        rx.button(
            "Next",
            on_click=state.next_page,
            disabled=~state.has_more_page,
        ),
        spacing=SPACING_MEDIUM,
        align="center",
    )


def entity_sorting(state: rx.State) -> rx.Component:
    """Sorting controls for entities."""
    return rx.hstack(
        rx.text("Sort", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select(
            items=state.order_by_options,
            value=state.order_by_value,
            on_change=state.set_order_by,
            width="80px",
        ),
        rx.select(
            items=state.order_direction_options,
            value=state.order_direction_value,
            on_change=state.set_order_direction,
            width="80px",
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def entity_list(
    state: rx.State,
    title: str,
    entities: rx.var,
    renderer_entity_row: Callable,
    no_entities_message: str,
    no_entities_description: str,
    delete_dialog: rx.Component,
    settings_dialog: rx.Component | None = None,
    filters: rx.Component | None = None,
    sorting: bool = False,
    pagination: bool = False,
) -> rx.Component:
    """Display list of entities with sorting and pagination."""
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading(title, size=HEADING_SIZE_SECTION),
                    rx.spacer(),
                    filters if filters else rx.fragment(),
                    entity_sorting(state) if sorting else rx.fragment(),
                    align="center",
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                rx.divider(),
                rx.cond(
                    state.entities_loading,
                    rx.center(
                        rx.spinner(size=SIZE_MEDIUM),
                        width="100%",
                        padding=PADDING_PAGE,
                    ),
                    rx.cond(
                        entities.length() > 0,
                        rx.vstack(
                            rx.foreach(iterable=entities, render_fn=lambda entity: renderer_entity_row(entity, bool(settings_dialog))),
                            spacing=SPACING_NONE,
                            width="100%",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("traffic-cone", size=ICON_SIZE_EMPTY_STATE, color=rx.color("mauve", 8)),
                                rx.text(
                                    no_entities_message,
                                    size=TEXT_SIZE_LARGE,
                                    color=rx.color("mauve", 10),
                                ),
                                rx.text(
                                    no_entities_description,
                                    size=TEXT_SIZE_LABEL,
                                    color=rx.color("mauve", 9),
                                ),
                                spacing=SPACING_SMALL,
                            ),
                            width="100%",
                            padding=PADDING_PAGE,
                        ),
                    ),
                ),
                rx.hstack(
                    entity_pagination(state),
                    width="100%",
                    justify="end",
                )
                if pagination
                else rx.spacer(),
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            width="100%",
        ),
        settings_dialog if settings_dialog else rx.fragment(),
        delete_dialog,
        spacing=SPACING_LARGE,
        width="100%",
    )
