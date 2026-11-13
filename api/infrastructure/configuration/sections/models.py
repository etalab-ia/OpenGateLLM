from typing import Annotated

from pydantic import Field, StringConstraints, field_validator, model_validator

from api.domain.provider.entities import BasicAuth, HostingZone, ProviderType
from api.domain.router.entities import RouterLoadBalancingStrategy, RouterType
from api.infrastructure.configuration._validationerrors import HiddenInputSchema, custom_validation_error

DEFAULT_TIMEOUT: int = 300
DEFAULT_PROVIDER_URLS = {
    ProviderType.ALBERT: "https://albert.api.etalab.gouv.fr/",
    ProviderType.MISTRAL: "https://albert.api.etalab.gouv.fr/",
    ProviderType.OPENAI: "https://api.openai.com/",
}


@custom_validation_error
class ModelProvider(HiddenInputSchema):
    type: Annotated[ProviderType, Field(description="Model provider type.")]
    url: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default=None, description="Model provider API url. The url must only contain the domain name (without `/v1` suffix for example). Depends of the model provider type, the url can be optional (Albert, OpenAI).")]  # fmt: off
    key: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default=None, description="Model provider API key.")]  # fmt: off
    basic_auth: Annotated[BasicAuth | None, Field(default=None, description="Model provider basic authentication.")]
    timeout: Annotated[int, Field(default=DEFAULT_TIMEOUT, description="Timeout for the model provider requests, after user receive an 503 error (model is too busy).")]  # fmt: off
    qos_limit: Annotated[int | None, Field(default=None, ge=0, description="Maximum concurrent load for this provider. If omitted, admission is unlimited.")]  # fmt: off
    model_name: Annotated[str, Field(description="Model name from the model provider.")]  # fmt: off
    model_hosting_zone: Annotated[HostingZone, Field(default=HostingZone.WOR, description="Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai")]  # fmt: off
    model_total_params: Annotated[int, Field(default=0, ge=0, description="Total params of the model in billions of parameters for carbon footprint computation. For more information, see https://ecologits.ai")]  # fmt: off
    model_active_params: Annotated[int, Field(default=0, ge=0, description="Active params of the model in billions of parameters for carbon footprint computation. For more information, see https://ecologits.ai")]  # fmt: off

    @field_validator("url", mode="after")
    def add_trailing_slash(cls, url):
        if url is not None and not url.endswith("/"):
            return f"{url}/"
        return url

    @model_validator(mode="after")
    def set_default_url(self):
        if self.url is None:
            if self.type not in DEFAULT_PROVIDER_URLS:
                raise ValueError("URL is required for this model provider type.")
            self.url = DEFAULT_PROVIDER_URLS[self.type]
        return self


@custom_validation_error
class Model(HiddenInputSchema):
    """
    In the model section, you define a list of models (routers and providers). These models are only used for the initial bootstrap of the API.
    The model section of the configuration is ignored if any models are already registered in the database.
    """

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64), Field(description="Unique name exposed to clients when selecting the model.", examples=["gpt-4o"])]  # fmt: off
    type: Annotated[RouterType, Field(description="Type of the model. It will be used to identify the model type.", examples=["text-generation"])]  # fmt: off
    aliases: Annotated[list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]], Field(default_factory=list, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]], json_schema_extra={"default": []})]  # fmt: off
    load_balancing_strategy: Annotated[RouterLoadBalancingStrategy, Field(default=RouterLoadBalancingStrategy.SHUFFLE, description="Routing strategy for load balancing between providers of the model.", examples=["least_busy"])]  # fmt: off
    cost_prompt_tokens: Annotated[float, Field(default=0.0, ge=0.0, description="Model costs prompt tokens for usage tracking. The cost is by 1M tokens.", examples=[0.1])]  # fmt: off
    cost_completion_tokens: Annotated[float, Field(default=0.0, ge=0.0, description="Model costs completion tokens for usage tracking. The cost is by 1M tokens. Set to `0.0` to disable cost computation for this model.", examples=[0.1])]  # fmt: off
    qos_retries_before_reject: Annotated[int | None, Field(default=None, ge=0, description="Number of admission retries before rejecting a saturated request. If omitted, admission is unlimited.")]  # fmt: off
    providers: Annotated[list[ModelProvider], Field(description="API providers of the model. If there are multiple providers, the model will be load balanced between them according to the routing strategy. The different models have to the same type.")]  # fmt: off

    @model_validator(mode="after")
    def validate_provider_type(self):
        for provider in self.providers:
            if not provider.type.is_compatible_with(router_type=self.type):
                raise ValueError(f"Provider type {provider.type.value} is not compatible with model type {self.type.value}")

        return self
