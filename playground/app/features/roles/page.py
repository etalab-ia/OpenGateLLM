"""Roles management page composition."""

import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.roles.components import (
    roles_header,
    roles_limits,
    roles_list,
    roles_permissions,
)


def roles_page() -> rx.Component:
    """Roles management page with admin permission check."""
    return rx.box(
        rx.scroll_area(
            rx.vstack(
                roles_header(),
                # Box 1: Roles list with sorting and pagination
                roles_list(),
                # Box 2: Limits management with filters
                roles_limits(),
                # Box 3: Permissions management
                roles_permissions(),
                spacing=SPACING_XL,
                width="100%",
                padding=PADDING_PAGE,
            ),
            height="100%",
        ),
        flex="1",
        width="100%",
        height="100vh",
        background_color=rx.color("mauve", 1),
    )
