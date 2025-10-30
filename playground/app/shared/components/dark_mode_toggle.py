"""Dark mode toggle component."""

import reflex as rx
from reflex.style import color_mode, set_color_mode


def dark_mode_toggle() -> rx.Component:
    """Toggle between light, dark, and system color modes.

    Returns:
        A segmented control component for switching color modes.
    """
    return rx.segmented_control.root(
        rx.segmented_control.item(
            rx.icon(tag="monitor", size=20),
            value="system",
        ),
        rx.segmented_control.item(
            rx.icon(tag="sun", size=20),
            value="light",
        ),
        rx.segmented_control.item(
            rx.icon(tag="moon", size=20),
            value="dark",
        ),
        on_change=set_color_mode,
        variant="classic",
        radius="large",
        value=color_mode,
    )
