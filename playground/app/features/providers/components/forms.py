import reflex as rx

from app.core.variables import SPACING_MEDIUM
from app.features.providers.state import ProvidersState
from app.shared.components.forms import entity_create_form, entity_form_input_field, entity_form_select_field


def provider_create_form_fields() -> rx.Component:
    """Fields of the provider create form."""
    return rx.grid(
        entity_form_select_field(
            label="API type*",
            items=ProvidersState.provider_types_list,
            value=ProvidersState.new_provider_type,
            on_change=ProvidersState.set_new_provider_type,
            placeholder="Select type",
        ),
        entity_form_input_field(
            label="Model name*",
            value=ProvidersState.new_provider_model_name,
            on_change=ProvidersState.set_new_provider_model_name,
            tooltip="Model name from the model API (e.g., gpt-4)",
            placeholder="Enter model name",
        ),
        entity_form_input_field(
            label="API url*",
            value=ProvidersState.new_provider_url,
            on_change=ProvidersState.set_new_provider_url,
            tooltip="API url of the model without /v1 (e.g., https://api.openai.com)",
            pattern="(http|https)://.*",
            placeholder="Enter API url",
        ),
        entity_form_input_field(
            label="API key",
            value=ProvidersState.new_provider_key,
            on_change=ProvidersState.set_new_provider_key,
            type="password",
            placeholder="Enter API key (optional)",
        ),
        entity_form_input_field(
            label="Timeout (seconds)",
            value=ProvidersState.new_provider_timeout,
            on_change=ProvidersState.set_new_provider_timeout,
            tooltip="Timeout for the API request in seconds (e.g., 300)",
            type="number",
            min=0,
            max=600,
        ),
        entity_form_select_field(
            label="Hosting country of model",
            items=ProvidersState.provider_carbon_footprint_zones_list,
            value=ProvidersState.new_provider_carbon_footprint_zone,
            on_change=ProvidersState.set_new_provider_carbon_footprint_zone,
            tooltip="Alpha-3 code of the country where the model is hosted for carbon footprint computation (e.g., FRA for France, USA for United States)",
        ),
        entity_form_input_field(
            label="Total params of the model",
            value=ProvidersState.new_provider_carbon_footprint_total_params,
            on_change=ProvidersState.set_new_provider_carbon_footprint_total_params,
            tooltip="Total params of the model in billions of parameters for carbon footprint computation (e.g., 100)",
            type="number",
            min=0,
            placeholder="Enter total params (optional)",
        ),
        entity_form_input_field(
            label="Active params of the model",
            value=ProvidersState.new_provider_carbon_footprint_active_params,
            on_change=ProvidersState.set_new_provider_carbon_footprint_active_params,
            tooltip="Active params of the model in billions of parameters for carbon footprint computation (e.g., 100)",
            type="number",
            min=0,
            placeholder="Enter active params (optional)",
        ),
        entity_form_select_field(
            label="Quality of service metric",
            items=ProvidersState.provider_qos_metric_list,
            value=ProvidersState.new_provider_qos_metric,
            on_change=ProvidersState.set_new_provider_qos_metric,
            tooltip="Metric to use for the quality of service policy. If not provided, no QoS policy is applied.",
        ),
        entity_form_input_field(
            label="Quality of service limit",
            value=ProvidersState.new_provider_qos_limit,
            on_change=ProvidersState.set_new_provider_qos_limit,
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
