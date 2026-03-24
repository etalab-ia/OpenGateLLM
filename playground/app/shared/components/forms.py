from collections.abc import Callable
from typing import Any

import reflex as rx

from app.core.variables import HEADING_SIZE_FORM, ICON_SIZE_TINY, SIZE_MEDIUM, SPACING_MEDIUM, SPACING_TINY, TEXT_SIZE_LABEL


def entity_form_select_field(
    label: str,
    items: rx.var,
    value: Any = None,
    on_change: Callable | None = None,
    disabled: bool = False,
    tooltip: str | None = None,
    **kwargs,
) -> rx.Component:
    normalized_value: Any = ""
    if value is None:
        normalized_value = ""
    elif hasattr(value, "to"):
        normalized_value = rx.cond(value != None, value.to(str), "")  # noqa: E711
    else:
        normalized_value = value

    return rx.vstack(
        rx.cond(
            bool(tooltip),
            rx.hstack(
                rx.text(label, size=TEXT_SIZE_LABEL, weight="bold"),
                rx.tooltip(
                    rx.icon("info", size=ICON_SIZE_TINY, color=rx.color("mauve", 10)),
                    content=tooltip,
                ),
                spacing=SPACING_TINY,
                align="center",
            ),
            rx.text(label, size=TEXT_SIZE_LABEL, weight="bold"),
        ),
        rx.select(
            items=items,
            value=normalized_value,
            on_change=on_change,
            disabled=disabled,
            **kwargs,
            width="100%",
        ),
        spacing=SPACING_TINY,
        width="100%",
    )


def entity_form_input_field(
    label: str,
    value: Any,
    on_change: Callable | None = None,
    tooltip: str | None = None,
    **kwargs: Any,
) -> rx.Component:
    normalized_value: Any = ""
    if value is None:
        normalized_value = ""
    elif hasattr(value, "to"):
        normalized_value = rx.cond(value != None, value.to(str), "")  # noqa: E711
    else:
        normalized_value = value

    return rx.vstack(
        rx.cond(
            bool(tooltip),
            rx.hstack(
                rx.text(label, size=TEXT_SIZE_LABEL, weight="bold"),
                rx.tooltip(
                    rx.icon("info", size=ICON_SIZE_TINY, color=rx.color("mauve", 10)),
                    content=tooltip,
                ),
                spacing=SPACING_TINY,
                align="center",
            ),
            rx.text(label, size=TEXT_SIZE_LABEL, weight="bold"),
        ),
        rx.input(
            value=normalized_value,
            on_change=on_change,
            width="100%",
            **kwargs,
        ),
        spacing=SPACING_TINY,
        width="100%",
    )


def entity_form_checkbox_field(
    label: str,
    value: Any,
    description: str | None = None,
    on_change: Callable | None = None,
    tooltip: str | None = None,
    **kwargs: Any,
) -> rx.Component:
    normalized_checked: Any = False
    if value is None:
        normalized_checked = False
    elif hasattr(value, "to"):
        normalized_checked = rx.cond(value != None, value.to(bool), False)  # noqa: E711
    else:
        normalized_checked = value

    return rx.hstack(
        rx.checkbox(
            checked=normalized_checked,
            on_change=on_change,
            **kwargs,
        ),
        rx.vstack(
            rx.cond(
                bool(tooltip),
                rx.hstack(
                    rx.text(label, size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=ICON_SIZE_TINY, color=rx.color("mauve", 10)),
                        content=tooltip,
                    ),
                    spacing=SPACING_TINY,
                    align="center",
                ),
                rx.text(label, size=TEXT_SIZE_LABEL, weight="bold"),
            ),
            rx.cond(
                bool(description),
                rx.text(description, size=TEXT_SIZE_LABEL),
            ),
            align="start",
            spacing="0",
        ),
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def entity_settings_form(state: rx.State, title: str, fields: rx.grid) -> rx.Component:
    """Form to display information about an entity and edit it."""
    return rx.card(
        rx.vstack(
            rx.heading(title, size=HEADING_SIZE_FORM),
            rx.divider(),
            fields,
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(
                        state.edit_entity_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Update",
                    ),
                    on_click=state.edit_entity,
                    disabled=state.edit_entity_loading,
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )


def entity_create_form(state: rx.State, title: str, fields: rx.grid) -> rx.Component:
    """Form to create a new entity."""
    return rx.card(
        rx.vstack(
            rx.heading(title, size=HEADING_SIZE_FORM),
            rx.divider(),
            fields,
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(
                        state.create_entity_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Create",
                    ),
                    on_click=state.create_entity,
                    disabled=state.create_entity_loading,
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )
