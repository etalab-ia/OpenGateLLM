import reflex as rx

from app.core.variables import SPACING_MEDIUM
from app.features.providers.state import ProvidersState
from app.shared.components.forms import entity_create_form, entity_form_input_field, entity_form_select_field


def provider_create_form_fields() -> rx.Component:
    """Fields of the provider create form."""
    return rx.grid(
        entity_form_select_field(
            label="Router*",
            items=ProvidersState.routers_name_list,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("router", value),
            placeholder="Select router",
        ),
        entity_form_select_field(
            label="API type*",
            items=ProvidersState.provider_types_list,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("type", value),
            placeholder="Select type",
        ),
        entity_form_input_field(
            label="API url",
            value=ProvidersState.entity_to_create.url,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("url", value),
            tooltip="API url of the model without /v1 (e.g., https://api.openai.com). If not provided, the url will be automatically set based on the type of the provider.",
            pattern="(http|https)://.*",
            placeholder="Enter API url",
        ),
        entity_form_input_field(
            label="API key",
            value=ProvidersState.entity_to_create.key,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("key", value),
            type="password",
            placeholder="Enter API key (optional)",
        ),
        entity_form_input_field(
            label="Model name*",
            value=ProvidersState.entity_to_create.model_name,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("model_name", value),
            tooltip="Model name from the model API (e.g., gpt-4)",
            placeholder="Enter model name",
        ),
        entity_form_input_field(
            label="Timeout (seconds)",
            value=ProvidersState.entity_to_create.timeout,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("timeout", value),
            tooltip="Timeout for the API request in seconds (default: 300)",
            type="number",
            min=0,
            max=600,
        ),
        entity_form_select_field(
            label="Hosting country of model",
            items=ProvidersState.provider_model_carbon_footprint_zones_list,
            value=ProvidersState.entity_to_create.model_carbon_footprint_zone,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("model_carbon_footprint_zone", value),
            tooltip="Alpha-3 code of the country where the model is hosted for carbon footprint computation (e.g., FRA for France, USA for United States)",
        ),
        entity_form_input_field(
            label="Total params of the model",
            value=ProvidersState.entity_to_create.model_carbon_footprint_total_params,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("model_carbon_footprint_total_params", value),
            tooltip="Total params of the model in billions of parameters for carbon footprint computation (e.g., 100)",
            type="number",
            min=0,
        ),
        entity_form_input_field(
            label="Active params of the model",
            value=ProvidersState.entity_to_create.model_carbon_footprint_active_params,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("model_carbon_footprint_active_params", value),
            tooltip="Active params of the model in billions of parameters for carbon footprint computation (e.g., 100)",
            type="number",
            min=0,
        ),
        entity_form_select_field(
            label="Quality of service metric",
            items=ProvidersState.provider_qos_metric_list,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("qos_metric", value),
            tooltip="Metric to use for the quality of service policy. If not provided, no QoS policy is applied.",
            placeholder="Select metric (optional)",
        ),
        entity_form_input_field(
            label="Quality of service limit",
            value=ProvidersState.entity_to_create.qos_limit,
            on_change=lambda value: ProvidersState.set_new_entity_attribut("qos_limit", value),
            type="number",
            min=0,
            placeholder="Enter limit (optional)",
            tooltip="Value to use for the quality of service (e.g., 100). Depends of the metric, the value can be a percentile, a threshold, etc. When limit is reach, model stop to accept requests to guarantee the quality of service",
        ),
        columns="2",
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def provider_create_form() -> rx.Component:
    """Form to create a new provider."""
    return entity_create_form(
        state=ProvidersState,
        title="Create new provider",
        fields=provider_create_form_fields(),
    )


def provider_settings_form_fields() -> rx.Component:
    return rx.grid(
        entity_form_input_field(
            label="API type",
            value=ProvidersState.entity.type,
            tooltip="API type of the provider",
            read_only=True,
        ),
        entity_form_input_field(
            label="API url",
            value=ProvidersState.entity.url,
            tooltip="API url of the provider",
            read_only=True,
            placeholder="No url",
        ),
        entity_form_input_field(
            label="API key",
            value=ProvidersState.entity.key,
            tooltip="API key of the provider",
            read_only=True,
            type="password",
            placeholder="No key",
        ),
        entity_form_input_field(
            label="Model name",
            value=ProvidersState.entity.model_name,
            tooltip="Model name of the provider",
            read_only=True,
        ),
        entity_form_select_field(
            label="Router",
            items=ProvidersState.routers_name_list,
            value=ProvidersState.entity.router,
            on_change=lambda value: ProvidersState.set_edit_entity_attribut("router", value),
            disable=ProvidersState.edit_entity_loading,
            tooltip="Router of the provider",
        ),
        entity_form_input_field(
            label="Timeout (seconds)",
            value=ProvidersState.entity.timeout,
            tooltip="Timeout for the API request in seconds (e.g., 300)",
            type="number",
            on_change=lambda value: ProvidersState.set_edit_entity_attribut("timeout", value),
            disable=ProvidersState.edit_entity_loading,
        ),
        entity_form_input_field(
            label="Hosting country of model",
            value=ProvidersState.entity.model_carbon_footprint_zone,
            tooltip="Hosting country of the model",
            on_change=lambda value: ProvidersState.set_edit_entity_attribut("model_carbon_footprint_zone", value),
        ),
        entity_form_input_field(
            label="Total params of the model",
            value=ProvidersState.entity.model_carbon_footprint_total_params,
            tooltip="Total params of the model",
            type="number",
            on_change=lambda value: ProvidersState.set_edit_entity_attribut("model_carbon_footprint_total_params", value),
            disable=ProvidersState.edit_entity_loading,
            min=0,
            placeholder="No total params",
        ),
        entity_form_input_field(
            label="Active params of the model",
            value=ProvidersState.entity.model_carbon_footprint_active_params,
            tooltip="Active params of the model",
            type="number",
            on_change=lambda value: ProvidersState.set_edit_entity_attribut("model_carbon_footprint_active_params", value),
            disable=ProvidersState.edit_entity_loading,
            placeholder="No active params",
            min=0,
        ),
        entity_form_input_field(
            label="Quality of service metric",
            value=ProvidersState.entity.qos_metric,
            tooltip="Quality of service metric of the provider",
            type="text",
            on_change=lambda value: ProvidersState.set_edit_entity_attribut("qos_metric", value),
            disable=ProvidersState.edit_entity_loading,
            placeholder="No metric",
        ),
        entity_form_input_field(
            label="Quality of service limit",
            value=ProvidersState.entity.qos_limit,
            tooltip="Quality of service limit of the provider",
            type="number",
            on_change=lambda value: ProvidersState.set_edit_entity_attribut("qos_limit", value),
            disable=ProvidersState.edit_entity_loading,
            min=0,
            placeholder="No limit",
        ),
        columns="2",
        spacing=SPACING_MEDIUM,
        width="100%",
    )
