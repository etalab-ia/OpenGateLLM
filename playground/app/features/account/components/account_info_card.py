"""Account information card component."""

import reflex as rx

from app.core.variables import HEADING_SIZE_SECTION, MARGIN_SMALL, SPACING_MEDIUM, SPACING_TINY, TEXT_SIZE_LABEL
from app.features.account.state import AccountState


def account_info_card() -> rx.Component:
    """Card displaying user information with edit functionality."""
    return rx.card(
        rx.vstack(
            rx.heading(
                "Information",
                size=HEADING_SIZE_SECTION,
                margin_bottom=MARGIN_SMALL,
            ),
            rx.divider(),
            rx.vstack(
                rx.vstack(
                    rx.text("Email", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        value=AccountState.user_email,
                        read_only=True,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Name", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Name",
                        value=AccountState.edit_name,
                        on_change=AccountState.set_edit_name,
                        on_mount=AccountState.load_current_name,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Budget", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        value=AccountState.user_budget_formatted,
                        read_only=True,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Save",
                        on_click=AccountState.update_name,
                        loading=AccountState.update_name_loading,
                        disabled=AccountState.update_name_loading,
                    ),
                    width="100%",
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )
