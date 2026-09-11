import reflex as rx

from app.core.variables import SPACING_MEDIUM
from app.features.routers.state import RoutersState
from app.shared.components.forms import (
    entity_create_form,
    entity_form_input_field,
    entity_form_select_field,
    entity_form_switch_field,
)


def router_settings_form_fields() -> rx.Component:
    """Fields of the router settings form."""
    return rx.grid(
        entity_form_input_field(
            label="Name",
            value=RoutersState.entity.name,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("name", value),
            tooltip="Router name corresponding to the model will be called by users (e.g., my-model)",
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_select_field(
            label="Type",
            items=RoutersState.router_types_list,
            value=RoutersState.entity.type,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("type", value),
            tooltip="Router type corresponds to the type of the model that will be served (e.g., text-generation for LLM)",
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="Aliases",
            value=RoutersState.entity.aliases,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("aliases", value),
            type="list",
            disable=RoutersState.edit_entity_loading,
            placeholder="No aliases",
        ),
        entity_form_select_field(
            label="Load balancing strategy",
            items=RoutersState.router_load_balancing_strategies_list,
            value=RoutersState.entity.load_balancing_strategy,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("load_balancing_strategy", value),
            tooltip="Strategy to use for load balancing between providers of the router",
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_switch_field(
            label="QoS",
            value=RoutersState.entity.qos_enable,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("qos_enable", value),
            description="Admit requests when providers are full; off disables protection",
            disabled=RoutersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="QoS retry",
            value=RoutersState.entity.qos_retry,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("qos_retry", value),
            tooltip="Max retries after the first FULL admission response (0 = immediate 503)",
            type="number",
            min=0,
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_select_field(
            label="QoS metric",
            items=RoutersState.router_qos_metrics_list,
            value=RoutersState.entity.qos_metric,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("qos_metric", value),
            tooltip="Load metric used for admission and health saturation",
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="QoS health threshold (orange)",
            value=RoutersState.entity.qos_health_threshold_start,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("qos_health_threshold_start", value),
            tooltip="Orange saturation ratio (e.g. 0.9)",
            type="number",
            min=0,
            step=0.1,
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="QoS health threshold (red)",
            value=RoutersState.entity.qos_health_threshold_end,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("qos_health_threshold_end", value),
            tooltip="Red saturation ratio (e.g. 1.1)",
            type="number",
            min=0,
            step=0.1,
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="Prompt tokens cost",
            value=RoutersState.entity.cost_prompt_tokens,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("cost_prompt_tokens", value),
            tooltip="Cost of a million prompt tokens, decrease user budget. If 0, no cost is applied.",
            type="number",
            min=0,
            disable=RoutersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="Completion tokens cost",
            value=RoutersState.entity.cost_completion_tokens,
            on_change=lambda value: RoutersState.set_edit_entity_attribut("cost_completion_tokens", value),
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
            value=RoutersState.entity_to_create.name,
            on_change=lambda value: RoutersState.set_new_entity_attribut("name", value),
            tooltip="Router name corresponds to the name of the model that will be called by the user (e.g., my-model)",
            disable=RoutersState.create_entity_loading,
            placeholder="Enter router name",
        ),
        entity_form_select_field(
            label="Type",
            items=RoutersState.router_types_list,
            value=RoutersState.entity_to_create.type,
            on_change=lambda value: RoutersState.set_new_entity_attribut("type", value),
            tooltip="Router type (e.g., text-generation)",
            placeholder="Select type",
        ),
        entity_form_input_field(
            label="Aliases",
            value=RoutersState.entity_to_create.aliases,
            on_change=lambda value: RoutersState.set_new_entity_attribut("aliases", value),
            type="list",
            placeholder="Enter aliases (comma-separated)",
            tooltip="Aliases of the router (e.g., alias1, alias2)",
        ),
        entity_form_select_field(
            label="Load balancing strategy",
            items=RoutersState.router_load_balancing_strategies_list,
            value=RoutersState.entity_to_create.load_balancing_strategy,
            on_change=lambda value: RoutersState.set_new_entity_attribut("load_balancing_strategy", value),
            tooltip="Strategy to use for load balancing between providers of the router",
            placeholder="Select strategy",
        ),
        entity_form_switch_field(
            label="QoS",
            value=RoutersState.entity_to_create.qos_enable,
            on_change=lambda value: RoutersState.set_new_entity_attribut("qos_enable", value),
            description="Admit requests when providers are full; off disables protection",
            disabled=RoutersState.create_entity_loading,
        ),
        entity_form_input_field(
            label="QoS retry",
            value=RoutersState.entity_to_create.qos_retry,
            on_change=lambda value: RoutersState.set_new_entity_attribut("qos_retry", value),
            tooltip="Max retries after the first FULL admission response (0 = immediate 503)",
            type="number",
            min=0,
            disable=RoutersState.create_entity_loading,
        ),
        entity_form_select_field(
            label="QoS metric",
            items=RoutersState.router_qos_metrics_list,
            value=RoutersState.entity_to_create.qos_metric,
            on_change=lambda value: RoutersState.set_new_entity_attribut("qos_metric", value),
            tooltip="Load metric used for admission and health saturation",
            disable=RoutersState.create_entity_loading,
        ),
        entity_form_input_field(
            label="QoS health threshold (orange)",
            value=RoutersState.entity_to_create.qos_health_threshold_start,
            on_change=lambda value: RoutersState.set_new_entity_attribut("qos_health_threshold_start", value),
            tooltip="Orange saturation ratio (e.g. 0.9)",
            type="number",
            min=0,
            step=0.1,
            disable=RoutersState.create_entity_loading,
        ),
        entity_form_input_field(
            label="QoS health threshold (red)",
            value=RoutersState.entity_to_create.qos_health_threshold_end,
            on_change=lambda value: RoutersState.set_new_entity_attribut("qos_health_threshold_end", value),
            tooltip="Red saturation ratio (e.g. 1.1)",
            type="number",
            min=0,
            step=0.1,
            disable=RoutersState.create_entity_loading,
        ),
        entity_form_input_field(
            label="Prompt tokens cost",
            value=RoutersState.entity_to_create.cost_prompt_tokens,
            on_change=lambda value: RoutersState.set_new_entity_attribut("cost_prompt_tokens", value),
            tooltip="Cost of a million prompt tokens, decrease user budget. If 0, no cost is applied.",
            type="number",
            min=0,
        ),
        entity_form_input_field(
            label="Completion tokens cost",
            value=RoutersState.entity_to_create.cost_completion_tokens,
            on_change=lambda value: RoutersState.set_new_entity_attribut("cost_completion_tokens", value),
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
