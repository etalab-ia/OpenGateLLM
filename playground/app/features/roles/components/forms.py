import reflex as rx

from app.core.variables import SIZE_MEDIUM, SPACING_MEDIUM, SPACING_SMALL, TEXT_SIZE_MEDIUM
from app.features.roles.models import Role
from app.features.roles.state import RolesState
from app.shared.components.forms import entity_create_form, entity_form_checkbox_field, entity_form_input_field, entity_form_select_field


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
            on_change=lambda value: RolesState.set_edit_entity_attribut("permissions_create_public_collection", value),
            description="Allow creating public collections. Public collections are visible to all users.",
            disabled=RolesState.edit_entity_loading,
        ),
        entity_form_checkbox_field(
            label="Read metrics",
            value=RolesState.entity.permissions_read_metric,
            on_change=lambda value: RolesState.set_edit_entity_attribut("permissions_read_metric", value),
            description="Allow reading Prometheus metrics (by /metrics endpoint).",
            disabled=RolesState.edit_entity_loading,
        ),
        entity_form_checkbox_field(
            label="Provide models",
            value=RolesState.entity.permissions_provide_models,
            on_change=lambda value: RolesState.set_edit_entity_attribut("permissions_provide_models", value),
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
            on_change=lambda value: RolesState.set_new_entity_attribut("permissions_create_public_collection", value),
            description="Allow creating public collections. Public collections are visible to all users.",
        ),
        entity_form_checkbox_field(
            label="Read metrics",
            value=RolesState.entity_to_create.permissions_read_metric,
            on_change=lambda value: RolesState.set_new_entity_attribut("permissions_read_metric", value),
            description="Allow reading Prometheus metrics (by /metrics endpoint).",
        ),
        entity_form_checkbox_field(
            label="Provide models",
            value=RolesState.entity_to_create.permissions_provide_models,
            on_change=lambda value: RolesState.set_new_entity_attribut("permissions_provide_models", value),
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


def role_create_limit_form(role: Role) -> rx.Component:
    """Form to add limits for a model (all 4 types)."""
    return rx.vstack(
        rx.hstack(
            entity_form_select_field(
                label="Router*",
                items=RolesState.routers_name_list,
                on_change=lambda value: RolesState.set_new_limit_value("router", value),
                disabled=RolesState.create_limit_loading,
                placeholder="Select router",
                tooltip="Router",
            ),
            entity_form_input_field(
                label="RPM",
                value=RolesState.new_limit["rpm"],
                on_change=lambda value: RolesState.set_new_limit_value("rpm", value),
                disabled=RolesState.create_limit_loading,
                tooltip="Requests Per Minute",
                placeholder="Unlimited",
                type="number",
            ),
            entity_form_input_field(
                label="RPD",
                value=RolesState.new_limit["rpd"],
                on_change=lambda value: RolesState.set_new_limit_value("rpd", value),
                disabled=RolesState.create_limit_loading,
                tooltip="Requests Per Day",
                placeholder="Unlimited",
                type="number",
            ),
            entity_form_input_field(
                label="TPM",
                value=RolesState.new_limit["tpm"],
                on_change=lambda value: RolesState.set_new_limit_value("tpm", value),
                disabled=RolesState.create_limit_loading,
                tooltip="Tokens Per Minute",
                placeholder="Unlimited",
                type="number",
            ),
            entity_form_input_field(
                label="TPD",
                value=RolesState.new_limit["tpd"],
                tooltip="Tokens Per Day",
                placeholder="Unlimited",
                on_change=lambda value: RolesState.set_new_limit_value("tpd", value),
                disabled=RolesState.create_limit_loading,
                type="number",
            ),
            spacing=SPACING_SMALL,
            width="100%",
        ),
        rx.hstack(
            rx.spacer(),
            rx.button(
                rx.cond(
                    RolesState.create_limit_loading,
                    rx.spinner(size=SIZE_MEDIUM),
                    "Add",
                ),
                on_click=lambda: RolesState.create_limit(role=role),
                disabled=RolesState.create_limit_loading,
            ),
            width="100%",
        ),
        spacing=SPACING_MEDIUM,
        width="100%",
    )
