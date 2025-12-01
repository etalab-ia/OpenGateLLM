import reflex as rx

from app.core.variables import SPACING_MEDIUM
from app.features.organizations.state import OrganizationsState
from app.shared.components.forms import entity_create_form, entity_form_input_field


def organization_settings_form_fields() -> rx.Component:
    """Fields of the organization settings form."""
    return rx.grid(
        entity_form_input_field(
            label="Name",
            value=OrganizationsState.entity.name,
            on_change=lambda value: OrganizationsState.set_edit_entity_attribut("name", value),
            disabled=OrganizationsState.edit_entity_loading,
        ),
        columns="1",
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def organization_create_form_fields() -> rx.Component:
    """Fields of the organization create form."""
    return rx.grid(
        entity_form_input_field(
            label="Name*",
            value=OrganizationsState.entity_to_create.name,
            on_change=lambda value: OrganizationsState.set_new_entity_attribut("name", value),
            placeholder="Enter organization name",
        ),
        columns="1",
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def organization_create_form() -> rx.Component:
    """Form to create a new role."""
    return entity_create_form(
        state=OrganizationsState,
        title="Create new organization",
        fields=organization_create_form_fields(),
    )
