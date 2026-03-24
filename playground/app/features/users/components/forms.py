import reflex as rx

from app.core.configuration import configuration
from app.core.variables import (
    SPACING_MEDIUM,
)
from app.features.users.state import UsersState
from app.shared.components.forms import entity_create_form, entity_form_input_field, entity_form_select_field


def user_settings_form_fields() -> rx.Component:
    """Fields of the user settings form."""
    return rx.grid(
        entity_form_input_field(
            label="Email",
            value=UsersState.entity.email,
            on_change=lambda value: UsersState.set_edit_entity_attribut("email", value),
            disabled=UsersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="Name",
            value=UsersState.entity.name,
            on_change=lambda value: UsersState.set_edit_entity_attribut("name", value),
            disabled=UsersState.edit_entity_loading,
            placeholder="No name",
        ),
        entity_form_input_field(
            label="Password",
            value=UsersState.entity.password,
            on_change=lambda value: UsersState.set_edit_entity_attribut("password", value),
            disabled=UsersState.edit_entity_loading,
            type="password",
            placeholder="Edit password (optional)",
        ),
        entity_form_select_field(
            label="Role",
            items=UsersState.roles_name_list,
            value=UsersState.entity.role,
            on_change=lambda value: UsersState.set_edit_entity_attribut("role", value),
            placeholder="Select role",
        ),
        entity_form_select_field(
            label="Organization",
            items=UsersState.organizations_name_list,
            value=UsersState.entity.organization,
            on_change=lambda value: UsersState.set_edit_entity_attribut("organization", value),
            placeholder="No organization",
        ),
        entity_form_input_field(
            label="Budget",
            value=UsersState.entity.budget,
            on_change=lambda value: UsersState.set_edit_entity_attribut("budget", value),
            disabled=UsersState.edit_entity_loading,
            tooltip="If budget is empty, the user will have unlimited usage.",
            placeholder="Unlimited",
        ),
        entity_form_input_field(
            label="Expires at",
            value=UsersState.entity.expires,
            on_change=lambda value: UsersState.set_edit_entity_attribut("expires", value),
            tooltip="User account expiration date. Leave empty for no expiration.",
            placeholder="No expiration",
            type="date",
            disabled=UsersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="Priority",
            value=UsersState.entity.priority,
            on_change=lambda value: UsersState.set_edit_entity_attribut("priority", value),
            tooltip="Priority of the user. The higher the priority, the more requests the user can make.",
            placeholder="Enter priority (optional)",
            type="number",
            min=0,
            max=configuration.settings.routing_max_priority,
        ),
        columns="2",
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def user_create_form_fields() -> rx.Component:
    """Fields of the user create form."""
    return rx.grid(
        entity_form_input_field(
            label="Email*",
            value=UsersState.entity_to_create.email,
            on_change=lambda value: UsersState.set_new_entity_attribut("email", value),
            placeholder="Enter email",
        ),
        entity_form_input_field(
            label="Name",
            value=UsersState.entity_to_create.name,
            on_change=lambda value: UsersState.set_new_entity_attribut("name", value),
            placeholder="Enter user name (optional)",
        ),
        entity_form_input_field(
            label="Password*",
            value=UsersState.entity_to_create.password,
            on_change=lambda value: UsersState.set_new_entity_attribut("password", value),
            placeholder="Enter password",
            type="password",
        ),
        entity_form_select_field(
            label="Role*",
            items=UsersState.roles_name_list,
            on_change=lambda value: UsersState.set_new_entity_attribut("role", value),
            placeholder="Select role",
        ),
        entity_form_select_field(
            label="Organization",
            items=UsersState.organizations_name_list,
            on_change=lambda value: UsersState.set_new_entity_attribut("organization", value),
            placeholder="No organization",
        ),
        entity_form_input_field(
            label="Budget",
            value=UsersState.entity_to_create.budget,
            on_change=lambda value: UsersState.set_new_entity_attribut("budget", value),
            placeholder="Unlimited",
        ),
        entity_form_input_field(
            label="Expires at",
            value=UsersState.entity_to_create.expires,
            on_change=lambda value: UsersState.set_new_entity_attribut("expires", value),
            tooltip="User account expiration date. Leave empty for no expiration.",
            placeholder="No expiration",
            type="date",
        ),
        entity_form_input_field(
            label="Priority",
            value=UsersState.entity_to_create.priority,
            on_change=lambda value: UsersState.set_new_entity_attribut("priority", value),
            tooltip="Priority of the user. The higher the priority, the more requests the user can make.",
            type="number",
            placeholder="Enter priority (optional)",
            min=0,
            max=configuration.settings.routing_max_priority,
        ),
        columns="2",
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def user_create_form() -> rx.Component:
    """Form to create a new role."""
    return entity_create_form(
        state=UsersState,
        title="Create new user",
        fields=user_create_form_fields(),
    )
