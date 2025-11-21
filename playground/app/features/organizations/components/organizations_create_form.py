import reflex as rx

from app.core.variables import HEADING_SIZE_FORM, SIZE_MEDIUM, SPACING_MEDIUM
from app.features.organizations.state import OrganizationsState


def organizations_create_form() -> rx.Component:
    """Form to create a new organization."""
    return rx.card(
        rx.vstack(
            rx.heading("Create new organization", size=HEADING_SIZE_FORM),
            rx.input(
                placeholder="Organization name",
                value=OrganizationsState.new_organization_name,
                on_change=OrganizationsState.set_new_organization_name,
                disabled=OrganizationsState.create_organization_loading,
                width="100%",
            ),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(
                        OrganizationsState.create_organization_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Create",
                    ),
                    on_click=OrganizationsState.create_organization,
                    disabled=OrganizationsState.create_organization_loading,
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )
