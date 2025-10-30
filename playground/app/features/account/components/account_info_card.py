"""Account information card component."""

import reflex as rx

from app.features.account.state import AccountState


def account_info_card() -> rx.Component:
    """Card displaying user information with edit functionality."""
    return rx.card(
        rx.vstack(
            rx.heading(
                "Information",
                size="6",
                margin_bottom="0.5em",
            ),
            rx.divider(),
            rx.vstack(
                rx.vstack(
                    rx.text("Email", size="2", weight="bold"),
                    rx.input(
                        value=AccountState.user_email,
                        read_only=True,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Name", size="2", weight="bold"),
                    rx.input(
                        placeholder="Enter your name",
                        value=AccountState.edit_name,
                        on_change=AccountState.set_edit_name,
                        on_mount=AccountState.load_current_name,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Budget", size="2", weight="bold"),
                    rx.input(
                        value=AccountState.user_budget_formatted,
                        read_only=True,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.button(
                    rx.icon("save", size=18),
                    "Save",
                    on_click=AccountState.update_name,
                    loading=AccountState.update_name_loading,
                    disabled=AccountState.update_name_loading,
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        max_width="1000px",
    )
