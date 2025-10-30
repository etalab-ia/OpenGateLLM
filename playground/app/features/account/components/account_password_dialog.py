"""Password change dialog component."""

import reflex as rx

from app.features.account.state import AccountState


def account_password_dialog() -> rx.Component:
    """Dialog for changing password."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("lock", size=18),
                "Change Password",
                variant="soft",
                size="3",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Change Password"),
            rx.dialog.description(
                "Update your password. Make sure it's at least 8 characters long.",
            ),
            rx.vstack(
                rx.vstack(
                    rx.text("Current Password", size="2", weight="bold"),
                    rx.input(
                        placeholder="Enter current password",
                        type="password",
                        value=AccountState.current_password,
                        on_change=AccountState.set_current_password,
                        on_focus=AccountState.clear_password_messages,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("New Password", size="2", weight="bold"),
                    rx.input(
                        placeholder="Enter new password (min 8 characters)",
                        type="password",
                        value=AccountState.new_password,
                        on_change=AccountState.set_new_password,
                        on_focus=AccountState.clear_password_messages,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Confirm New Password", size="2", weight="bold"),
                    rx.input(
                        placeholder="Confirm new password",
                        type="password",
                        value=AccountState.confirm_password,
                        on_change=AccountState.set_confirm_password,
                        on_focus=AccountState.clear_password_messages,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.cond(
                    AccountState.password_change_error != "",
                    rx.callout(
                        AccountState.password_change_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        width="100%",
                    ),
                ),
                rx.cond(
                    AccountState.password_change_success != "",
                    rx.callout(
                        AccountState.password_change_success,
                        icon="check",
                        color_scheme="green",
                        width="100%",
                    ),
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
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="450px",
        ),
    )
