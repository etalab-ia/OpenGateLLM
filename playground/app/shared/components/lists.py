from collections.abc import Callable

from pydantic import BaseModel
import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    ICON_SIZE_EMPTY_STATE,
    ICON_SIZE_MEDIUM,
    MARGIN_MEDIUM,
    MAX_DIALOG_WIDTH,
    PADDING_PAGE,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_NONE,
    SPACING_SMALL,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_LARGE,
)
from app.shared.components.pagination import pagination


def entity_item_row(
    entity: BaseModel,
    state: rx.State,
    row_content: rx.Component,
    row_description: rx.Component,
    with_edit: bool = False,
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
                    with_edit,
                    rx.button(
                        rx.icon("pencil", size=ICON_SIZE_MEDIUM),
                        on_click=lambda: state.set_entity_to_edit(entity.id),
                        variant="soft",
                        color_scheme="blue",
                        size=TEXT_SIZE_LABEL,
                    ),
                ),
                rx.button(
                    rx.icon("trash-2", size=ICON_SIZE_MEDIUM),
                    on_click=lambda: state.set_entity_to_delete(entity.id),
                    variant="soft",
                    color_scheme="red",
                    size=TEXT_SIZE_LABEL,
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


def entity_delete_dialog(state: rx.State, title: str, description: str) -> rx.Component:
    """Dialog for deleting an entity."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title(title),
            rx.alert_dialog.description(description),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Delete",
                        on_click=lambda: state.delete_entity(state.entity_to_delete),
                        color_scheme="red",
                        loading=state.delete_entity_loading,
                    ),
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
                width="100%",
            ),
            spacing=SPACING_LARGE,
        ),
        open=state.is_delete_entity_dialog_open,
        on_open_change=state.handle_delete_entity_dialog_change,
    )


def entity_edit_dialog(state: rx.State, title: str | None, fields: rx.Component | None) -> rx.Component:
    """Dialog for editing an entity."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(title),
            fields,
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=lambda: state.set_entity_to_edit(None),
                    ),
                ),
                rx.button(
                    rx.cond(
                        state.edit_entity_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Update",
                    ),
                    on_click=state.update_entity,
                    disabled=state.edit_entity_loading,
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
                margin_top=MARGIN_MEDIUM,
            ),
            max_width=MAX_DIALOG_WIDTH,
        ),
        open=state.is_edit_entity_dialog_open,
    )


def entity_list(
    state: rx.State,
    title: str,
    entities: rx.var,
    renderer_entity_row: Callable,
    delete_title: str,
    delete_description: str,
    no_entities_message: str,
    no_entities_description: str,
    edit_title: str | None = None,
    edit_fields: rx.Component | None = None,
    with_edit: bool = False,
    with_pagination: bool = False,
) -> rx.Component:
    """Display list of entities with sorting and pagination."""
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading(title, size=HEADING_SIZE_SECTION),
                    rx.badge(
                        entities.length(),
                        variant="soft",
                        color_scheme="blue",
                    ),
                    rx.spacer(),
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
                            rx.foreach(iterable=entities, render_fn=renderer_entity_row),
                            spacing=SPACING_NONE,
                            width="100%",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("building", size=ICON_SIZE_EMPTY_STATE, color=rx.color("mauve", 8)),
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
                rx.cond(
                    with_pagination,
                    rx.hstack(
                        pagination(state),
                        width="100%",
                        justify="end",
                    ),
                ),
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            width="100%",
        ),
        rx.cond(
            with_edit,
            entity_edit_dialog(state, title=edit_title, fields=edit_fields),
        ),
        entity_delete_dialog(state, title=delete_title, description=delete_description),
        spacing=SPACING_LARGE,
        width="100%",
    )
