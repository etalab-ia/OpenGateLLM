import reflex as rx

from app.core.variables import HEADING_SIZE_FORM, SIZE_MEDIUM, SPACING_MEDIUM
from app.features.keys.state import KeysState
from app.shared.components.forms import entity_form_input_field


def keys_create_form_fields() -> rx.Component:
    """Fields of the key create form."""
    return rx.grid(
        entity_form_input_field(
            label="Name*",
            value=KeysState.entity_to_create.name,
            on_change=lambda value: KeysState.set_new_entity_attribut("name", value),
            placeholder="Enter key name",
        ),
        entity_form_input_field(
            label="Expires at",
            value=KeysState.entity_to_create.expires,
            on_change=lambda value: KeysState.set_new_entity_attribut("expires", value),
            tooltip="Key expiration date. Leave empty for no expiration.",
            placeholder="No expiration",
            min=KeysState.min_expiry_date,
            max=KeysState.max_expiry_date,
            type="date",
        ),
        columns="2",
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def keys_create_form() -> rx.Component:
    """Form to create a new API key."""
    return rx.card(
        rx.vstack(
            rx.heading("Create new API key", size=HEADING_SIZE_FORM),
            rx.divider(),
            keys_create_form_fields(),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(KeysState.create_entity_loading, rx.spinner(size=SIZE_MEDIUM), "Create"),
                    on_click=KeysState.create_entity,
                    disabled=KeysState.create_entity_loading,
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )
