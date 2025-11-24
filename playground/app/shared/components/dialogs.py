import reflex as rx

from app.core.variables import MARGIN_MEDIUM, MAX_DIALOG_WIDTH, SIZE_MEDIUM, SPACING_LARGE, SPACING_MEDIUM


def entity_info_dialog(state: rx.State, title: str, description: str, fields: rx.Component | None) -> rx.Component:
    """Dialog for displaying information about an entity."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(title),
            rx.dialog.description(description),
            fields,
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "Close",
                        variant="soft",
                        color_scheme="gray",
                    ),
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
                margin_top=MARGIN_MEDIUM,
            ),
            max_width=MAX_DIALOG_WIDTH,
        ),
    )


def entity_edit_dialog(state: rx.State, title: str, fields: rx.grid) -> rx.Component:
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
                        on_click=lambda: state.set_entity_to_edit(entity=None),
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
        on_open_change=state.handle_edit_entity_dialog_change,
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
                        on_click=lambda: state.delete_entity(),
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
