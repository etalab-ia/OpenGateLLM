"""Password change card component."""

import reflex as rx

from app.core.variables import ICON_SIZE_TINY, MARGIN_SMALL, SPACING_MEDIUM, SPACING_TINY, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.account.state import AccountState


def account_password_card() -> rx.Component:
    """Card for changing password."""
    return rx.card(
        rx.vstack(
            rx.heading(
                "Change password",
                size=TEXT_SIZE_LARGE,
                margin_bottom=MARGIN_SMALL,
            ),
            rx.divider(),
            rx.vstack(
                rx.vstack(
                    rx.text("Current password", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Current password",
                        type="password",
                        value=AccountState.current_password,
                        on_change=AccountState.set_current_password,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("New password", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.tooltip(
                            rx.icon("info", size=ICON_SIZE_TINY, color=rx.color("mauve", 10)),
                            content="The new password must be at least 8 characters long.",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.input(
                        placeholder="New password",
                        type="password",
                        value=AccountState.new_password,
                        on_change=AccountState.set_new_password,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Confirm new password", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.tooltip(
                            rx.icon("info", size=ICON_SIZE_TINY, color=rx.color("mauve", 10)),
                            content="The new password and the confirm new password must be the same.",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.input(
                        placeholder="New password",
                        type="password",
                        value=AccountState.confirm_password,
                        on_change=AccountState.set_confirm_password,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Update",
                        on_click=AccountState.change_password,
                        loading=AccountState.password_change_loading,
                        disabled=AccountState.password_change_loading,
                    ),
                    width="100%",
                ),
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )
