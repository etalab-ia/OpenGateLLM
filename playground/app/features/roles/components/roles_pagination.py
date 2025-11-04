import reflex as rx

from app.core.variables import SPACING_MEDIUM
from app.features.roles.state import RolesState


def roles_pagination() -> rx.Component:
    """Pagination controls for roles list."""
    return rx.hstack(
        rx.button(
            "Prev",
            on_click=RolesState.prev_roles_page,
            disabled=RolesState.roles_page <= 1,
        ),
        rx.text(
            RolesState.roles_page.to(str) + " / " + RolesState.roles_total_pages.to(str),
        ),
        rx.button(
            "Next",
            on_click=RolesState.next_roles_page,
            disabled=~RolesState.has_more_roles,
        ),
        spacing=SPACING_MEDIUM,
        align="center",
    )
