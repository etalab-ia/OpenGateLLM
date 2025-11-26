import reflex as rx

from app.core.variables import SPACING_MEDIUM, TEXT_SIZE_MEDIUM
from app.features.roles.state import RolesState
from app.shared.components.forms import entity_create_form, entity_form_checkbox_field, entity_form_input_field


def role_settings_form_fields() -> rx.Component:
    """Fields of the role settings form."""
    return rx.grid(
        entity_form_input_field(
            label="Name*",
            value=RolesState.entity.name,
            on_change=lambda value: RolesState.set_edit_entity_attribut("name", value),
            disabled=RolesState.edit_entity_loading,
        ),
        entity_form_checkbox_field(
            label="Admin",
            value=RolesState.entity.permissions_admin,
            on_change=lambda value: RolesState.set_edit_entity_attribut("permissions_admin", value),
            description="Give admistration rights to manage users, roles, and permissions.",
            disabled=RolesState.edit_entity_loading,
        ),
        entity_form_checkbox_field(
            label="Create public collection",
            value=RolesState.entity.permissions_create_public_collection,
            on_change=lambda value: RolesState.set_edit_entity_attribut("create_public_collection", value),
            description="Allow creating public collections. Public collections are visible to all users.",
            disabled=RolesState.edit_entity_loading,
        ),
        entity_form_checkbox_field(
            label="Read metrics",
            value=RolesState.entity.permissions_read_metric,
            on_change=lambda value: RolesState.set_edit_entity_attribut("read_metrics", value),
            description="Allow reading Prometheus metrics (by /metrics endpoint).",
            disabled=RolesState.edit_entity_loading,
        ),
        entity_form_checkbox_field(
            label="Provide models",
            value=RolesState.entity.permissions_provide_models,
            on_change=lambda value: RolesState.set_edit_entity_attribut("provide_models", value),
            description="Allow add and remove model providers for the model routers.",
            disabled=RolesState.edit_entity_loading,
        ),
        columns="1",
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def role_create_form_fields() -> rx.Component:
    """Fields of the role create form."""
    return rx.grid(
        entity_form_input_field(
            label="Name*",
            value=RolesState.entity_to_create.name,
            on_change=lambda value: RolesState.set_new_entity_attribut("name", value),
            placeholder="Enter role name",
        ),
        rx.text("Special permissions", size=TEXT_SIZE_MEDIUM, weight="bold"),
        entity_form_checkbox_field(
            label="Admin",
            value=RolesState.entity_to_create.permissions_admin,
            on_change=lambda value: RolesState.set_new_entity_attribut("permissions_admin", value),
            description="Give admistration rights to manage users, roles, and permissions.",
        ),
        entity_form_checkbox_field(
            label="Create public collection",
            value=RolesState.entity_to_create.permissions_create_public_collection,
            on_change=lambda value: RolesState.set_new_entity_attribut("create_public_collection", value),
            description="Allow creating public collections. Public collections are visible to all users.",
        ),
        entity_form_checkbox_field(
            label="Read metrics",
            value=RolesState.entity_to_create.permissions_read_metric,
            on_change=lambda value: RolesState.set_new_entity_attribut("read_metrics", value),
            description="Allow reading Prometheus metrics (by /metrics endpoint).",
        ),
        entity_form_checkbox_field(
            label="Provide models",
            value=RolesState.entity_to_create.permissions_provide_models,
            on_change=lambda value: RolesState.set_new_entity_attribut("provide_models", value),
            description="Allow add and remove model providers for the model routers.",
        ),
        columns="1",
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def role_create_form() -> rx.Component:
    """Form to create a new role."""
    return entity_create_form(
        state=RolesState,
        title="Create new role",
        fields=role_create_form_fields(),
    )
