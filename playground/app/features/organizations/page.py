"""Organizations page."""

import reflex as rx

from app.core.variables import PADDING_PAGE, SPACING_XL
from app.features.organizations.components import organizations_header, organizations_list


def organizations_page() -> rx.Component:
    """Main organizations page."""
    return rx.box(
        rx.vstack(
            organizations_header(),
            organizations_list(),
            spacing=SPACING_XL,
            width="100%",
        ),
        padding=PADDING_PAGE,
        width="100%",
    )
