"""Password change dialog component."""

import reflex as rx

from app.core.variables import (
    ICON_SIZE_MEDIUM,
    MAX_DIALOG_WIDTH,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
)
from app.features.account.state import AccountState


def account_password_dialog() -> rx.Component:
    """Dialog for changing password."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("lock", size=ICON_SIZE_MEDIUM),
                "Change Password",
                variant="soft",
                size=SIZE_MEDIUM,
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Change Password"),
            rx.dialog.description(
                "Update your password. Make sure it's at least 8 characters long.",
            ),
            rx.vstack(
                rx.vstack(
                    rx.text("Current Password", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Enter current password",
                        type="password",
                        value=AccountState.current_password,
                        on_change=AccountState.set_current_password,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("New Password", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Enter new password (min 8 characters)",
                        type="password",
                        value=AccountState.new_password,
                        on_change=AccountState.set_new_password,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Confirm New Password", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Confirm new password",
                        type="password",
                        value=AccountState.confirm_password,
                        on_change=AccountState.set_confirm_password,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                        ),
                    ),
                    rx.button(
                        "Update Password",
                        on_click=AccountState.change_password,
                        loading=AccountState.password_change_loading,
                        disabled=AccountState.password_change_loading,
                    ),
                    spacing=SPACING_MEDIUM,
                    justify="end",
                    width="100%",
                ),
                spacing=SPACING_LARGE,
                width="100%",
            ),
            max_width=MAX_DIALOG_WIDTH,
        ),
    )
