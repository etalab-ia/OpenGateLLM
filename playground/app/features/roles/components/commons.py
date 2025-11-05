import reflex as rx

from app.core.variables import SIZE_SMALL, SPACING_SMALL, TEXT_SIZE_LABEL


def permission_checkbox_item(
    permission_key: str,
    title: str,
    description: str,
    permissions_list,
    toggle_handler,
    disabled: bool = False,
):
    """Generic permission checkbox item."""
    return rx.hstack(
        rx.checkbox(
            checked=permissions_list.contains(permission_key),
            on_change=lambda checked: toggle_handler(permission_key, checked),
            spacing=SPACING_SMALL,
            size=SIZE_SMALL,
            disabled=disabled,
        ),
        rx.vstack(
            rx.text(title, size=TEXT_SIZE_LABEL, weight="bold"),
            rx.text(description, size=TEXT_SIZE_LABEL),
            align="start",
            spacing="0",
        ),
    )
