import reflex as rx

from app.core.variables import SELECT_MEDIUM_WIDTH, SPACING_SMALL, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.keys.components.dialogs import keys_delete_dialog
from app.features.keys.models import Key
from app.features.keys.state import KeysState
from app.shared.components.lists import entity_list, entity_row


def key_row_content(key: Key) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                key.name,
                size=TEXT_SIZE_LARGE,
                weight="bold",
                color=rx.cond(key.is_expired, rx.color("mauve", 9), rx.color("mauve", 12)),
            ),
            rx.tooltip(
                rx.badge(
                    key.id.to(str),
                    variant="soft",
                    color_scheme="blue",
                ),
                content="ID",
            ),
            rx.cond(
                key.is_expired,
                rx.tooltip(
                    rx.badge(
                        "Expired",
                        variant="soft",
                        color_scheme="red",
                    ),
                    content="This key has expired and can no longer be used.",
                ),
            ),
            spacing=SPACING_SMALL,
        ),
        rx.hstack(
            rx.text(
                "Token:",
                size=TEXT_SIZE_LABEL,
                weight="bold",
                color=rx.color("mauve", 11),
            ),
            rx.code(
                rx.cond(
                    key.token.length() > 40,
                    key.token[:40] + "...",
                    key.token,
                ),
                size="2",
            ),
            spacing="2",
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def key_row_description(key: Key) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                f"Created: {key.created} • Expires: ",
                size=TEXT_SIZE_LABEL,
                color=rx.color("mauve", 9),
            ),
            rx.text(
                key.expires,
                size=TEXT_SIZE_LABEL,
                weight=rx.cond(key.is_expired, "bold", "regular"),
                color=rx.cond(key.is_expired, rx.color("red", 10), rx.color("mauve", 9)),
            ),
            spacing="1",
            align="center",
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def key_renderer_row(key: Key, with_settings: bool = False) -> rx.Component:
    """Display a row with user information."""
    return entity_row(
        state=KeysState,
        entity=key,
        row_content=key_row_content(key),
        row_description=key_row_description(key),
        with_settings=with_settings,
    )


def key_filters() -> rx.Component:
    """Filters for keys list."""
    return rx.hstack(
        rx.text("Status", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select(
            KeysState.status_filter_options,
            on_change=KeysState.set_status_filter,
            value=KeysState.status_filter_value,
            width=SELECT_MEDIUM_WIDTH,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def keys_list() -> rx.Component:
    """Keys list."""
    return entity_list(
        state=KeysState,
        title="Keys",
        entities=KeysState.keys,
        renderer_entity_row=key_renderer_row,
        no_entities_message="No keys yet",
        no_entities_description="Create your first key to get started",
        delete_dialog=keys_delete_dialog(),
        filters=key_filters(),
        pagination=True,
        sorting=True,
    )
