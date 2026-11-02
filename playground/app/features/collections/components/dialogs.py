import reflex as rx

from app.features.collections.state import CollectionsState


def collection_fields(editing: bool = False) -> rx.Component:
    state = CollectionsState.entity if editing else CollectionsState.entity_to_create
    setter = CollectionsState.set_edit_entity_attribut if editing else CollectionsState.set_new_entity_attribut
    return rx.vstack(
        rx.vstack(
            rx.text("Name", size="2", weight="bold"),
            rx.input(
                value=state.name,
                on_change=lambda value: setter("name", value),
                placeholder="e.g. Administrative guides",
                aria_label="Name",
                required=True,
                width="100%",
            ),
            spacing="1",
            align="start",
            width="100%",
        ),
        rx.vstack(
            rx.text("Description", size="2", weight="bold"),
            rx.text_area(
                value=state.description,
                on_change=lambda value: setter("description", value),
                placeholder="What belongs in this collection?",
                aria_label="Description",
                width="100%",
                min_height="90px",
            ),
            spacing="1",
            align="start",
            width="100%",
        ),
        rx.vstack(
            rx.text("Visibility", size="2", weight="bold"),
            rx.select(
                ["private", "public"],
                value=state.visibility,
                on_change=lambda value: setter("visibility", value),
                width="100%",
            ),
            rx.text(
                "Private collections are only visible to you. Public collections can be read by everyone.",
                size="1",
                color=rx.color("mauve", 10),
            ),
            spacing="1",
            align="start",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


def collection_create_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("New collection"),
            rx.dialog.description("Create a collection to organize your documents."),
            collection_fields(),
            rx.hstack(
                rx.dialog.close(
                    rx.button("Cancel", variant="soft", color_scheme="gray", disabled=CollectionsState.create_entity_loading),
                ),
                rx.button("Create collection", on_click=CollectionsState.create_entity, loading=CollectionsState.create_entity_loading),
                justify="end",
                spacing="3",
                width="100%",
                margin_top="1em",
            ),
            max_width="480px",
        ),
        open=CollectionsState.is_create_dialog_open,
        on_open_change=CollectionsState.handle_create_dialog_change,
    )


def collection_settings_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Edit collection"),
            rx.dialog.description("Update the collection name, description or visibility."),
            collection_fields(editing=True),
            rx.hstack(
                rx.dialog.close(
                    rx.button("Cancel", variant="soft", color_scheme="gray", disabled=CollectionsState.edit_entity_loading),
                ),
                rx.button("Save changes", on_click=CollectionsState.edit_entity, loading=CollectionsState.edit_entity_loading),
                justify="end",
                spacing="3",
                width="100%",
                margin_top="1em",
            ),
            max_width="480px",
        ),
        open=CollectionsState.is_settings_entity_dialog_open,
        on_open_change=CollectionsState.handle_settings_entity_dialog_change,
    )


def collection_delete_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete collection"),
            rx.alert_dialog.description("Delete this collection and its documents? This action cannot be undone."),
            rx.hstack(
                rx.alert_dialog.cancel(rx.button("Cancel", variant="soft", color_scheme="gray", disabled=CollectionsState.delete_entity_loading)),
                rx.alert_dialog.action(
                    rx.button("Delete", color_scheme="red", on_click=CollectionsState.delete_entity, loading=CollectionsState.delete_entity_loading)
                ),
                justify="end",
                spacing="3",
                width="100%",
            ),
        ),
        open=CollectionsState.is_delete_entity_dialog_open,
        on_open_change=CollectionsState.handle_delete_entity_dialog_change,
    )
