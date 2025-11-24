import reflex as rx

from app.core.variables import SPACING_MEDIUM
from app.features.routers.state import RoutersState
from app.shared.components.forms import entity_create_form, entity_form_input_field, entity_form_select_field


def router_edit_form_fields() -> rx.Component:
    """Fields of the router edit form."""
    return rx.grid(
        entity_form_input_field(
            label="Name",
            value=RoutersState.edit_router_name,
            on_change=RoutersState.set_edit_router_name,
            tooltip="Router name corresponding to the model will be called by users (e.g., my-model)",
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_select_field(
            label="Type",
            items=RoutersState.router_types_list,
            value=RoutersState.edit_router_type,
            on_change=RoutersState.set_new_router_type,
            tooltip="Router type corresponds to the type of the model that will be served (e.g., text-generation for LLM)",
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="Aliases",
            value=RoutersState.edit_router_aliases,
            on_change=RoutersState.set_edit_router_aliases,
            type="list",
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_select_field(
            label="Load balancing strategy",
            items=RoutersState.router_load_balancing_strategies_list,
            value=RoutersState.edit_router_load_balancing_strategy,
            on_change=RoutersState.set_edit_router_load_balancing_strategy,
            tooltip="Strategy to use for load balancing between providers of the router",
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="Prompt tokens cost",
            value=RoutersState.edit_router_cost_prompt_tokens,
            on_change=RoutersState.set_edit_router_cost_prompt_tokens,
            tooltip="Cost of a million prompt tokens, decrease user budget. If 0, no cost is applied.",
            type="number",
            min=0,
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="Completion tokens cost",
            value=RoutersState.edit_router_cost_completion_tokens,
            on_change=RoutersState.set_edit_router_cost_completion_tokens,
            tooltip="Cost of a million completion tokens, decrease user budget. If 0, no cost is applied.",
            type="number",
            min=0,
            disable=RoutersState.edit_entity_loading,
        ),
        columns="2",
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def router_create_form_fields() -> rx.Component:
    """Fields of the router create form."""
    return rx.grid(
        entity_form_input_field(
            label="Name*",
            value=RoutersState.new_router_name,
            on_change=RoutersState.set_new_router_name,
            tooltip="Router name corresponds to the name of the model that will be called by the user (e.g., my-model)",
            disable=RoutersState.create_entity_loading,
            placeholder="Enter router name",
        ),
        entity_form_select_field(
            label="Type",
            items=RoutersState.router_types_list,
            value=RoutersState.new_router_type,
            on_change=RoutersState.set_new_router_type,
            tooltip="Router type (e.g., text-generation)",
        ),
        entity_form_input_field(
            label="Aliases",
            value=RoutersState.new_router_aliases,
            on_change=RoutersState.set_new_router_aliases,
            type="list",
            placeholder="Enter aliases (comma-separated)",
            tooltip="Aliases of the router (e.g., alias1, alias2)",
        ),
        entity_form_select_field(
            label="Load balancing strategy",
            items=RoutersState.router_load_balancing_strategies_list,
            value=RoutersState.new_router_load_balancing_strategy,
            on_change=RoutersState.set_new_router_load_balancing_strategy,
            tooltip="Strategy to use for load balancing between providers of the router",
        ),
        entity_form_input_field(
            label="Prompt tokens cost",
            value=RoutersState.new_router_cost_prompt_tokens,
            on_change=RoutersState.set_new_router_cost_prompt_tokens,
            tooltip="Cost of a million prompt tokens, decrease user budget. If 0, no cost is applied.",
            type="number",
            min=0,
        ),
        entity_form_input_field(
            label="Completion tokens cost",
            value=RoutersState.new_router_cost_completion_tokens,
            on_change=RoutersState.set_new_router_cost_completion_tokens,
            tooltip="Cost of a million completion tokens, decrease user budget. If 0, no cost is applied.",
            type="number",
            min=0,
        ),
        columns="2",
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def router_create_form() -> rx.Component:
    """Form to create a new router."""
    return entity_create_form(
        state=RoutersState,
        title="Create new router",
        fields=router_create_form_fields(),
    )
