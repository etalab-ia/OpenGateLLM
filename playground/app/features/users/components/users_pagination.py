import reflex as rx

from app.core.variables import SPACING_MEDIUM
from app.features.users.state import UsersState


def users_pagination() -> rx.Component:
    """Pagination controls for users list."""
    return rx.hstack(
        rx.button(
            "Prev",
            on_click=UsersState.prev_users_page,
            disabled=UsersState.users_page <= 1,
        ),
        rx.text(
            UsersState.users_page.to(str) + " / " + UsersState.users_total_pages.to(str),
        ),
        rx.button(
            "Next",
            on_click=UsersState.next_users_page,
            disabled=~UsersState.has_more_users,
        ),
        spacing=SPACING_MEDIUM,
        align="center",
    )
