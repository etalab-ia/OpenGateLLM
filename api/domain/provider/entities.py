from enum import StrEnum

import pycountry

from api.domain import EntitiesPage
from api.domain.model.entities import ModelType
from api.domain.router.entities import Router
from api.schemas import BaseModel
from api.schemas.core.models import Metric

# Add world as a country code, default value of the carbon footprint computation framework
country_codes = [country.alpha_3 for country in pycountry.countries] + ["WOR"]
ProviderCarbonFootprintZone = StrEnum("ProviderCarbonFootprintZone", {str(code).upper(): str(code) for code in sorted(set(country_codes))})


class ProviderType(StrEnum):
    ALBERT = "albert"
    OPENAI = "openai"
    MISTRAL = "mistral"
    TEI = "tei"
    VLLM = "vllm"

    def is_compatible_with(self, router_type: ModelType) -> bool:
        return self.value in COMPATIBLE_PROVIDER_TYPES[router_type]


COMPATIBLE_PROVIDER_TYPES: dict[ModelType, list[str]] = {
    ModelType.AUTOMATIC_SPEECH_RECOGNITION: [
        ProviderType.ALBERT.value,
        ProviderType.MISTRAL.value,
        ProviderType.OPENAI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.IMAGE_TEXT_TO_TEXT: [
        ProviderType.ALBERT.value,
        ProviderType.MISTRAL.value,
        ProviderType.OPENAI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.TEXT_EMBEDDINGS_INFERENCE: [
        ProviderType.ALBERT.value,
        ProviderType.OPENAI.value,
        ProviderType.TEI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.TEXT_GENERATION: [
        ProviderType.ALBERT.value,
        ProviderType.MISTRAL.value,
        ProviderType.OPENAI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.TEXT_CLASSIFICATION: [
        ProviderType.ALBERT.value,
        ProviderType.TEI.value,
    ],
    ModelType.IMAGE_TO_TEXT: [
        ProviderType.MISTRAL.value,
    ],
}


class ProviderSortField(StrEnum):
    ID = "id"
    MODEL_NAME = "model_name"
    CREATED = "created"


ProviderPage = EntitiesPage["Provider"]


class Provider(BaseModel):
    id: int
    router_id: int
    user_id: int
    type: ProviderType
    url: str
    key: str | None = None
    timeout: int
    model_name: str
    model_hosting_zone: ProviderCarbonFootprintZone = ProviderCarbonFootprintZone.WOR
    model_total_params: int = 0
    model_active_params: int = 0
    qos_metric: Metric | None = None
    qos_limit: float | None = None
    created: int
    updated: int

    def with_router_id(self, router_id: int) -> "Provider":
        return self.model_copy(update={"router_id": router_id})

    def with_timeout(self, timeout: int) -> "Provider":
        return self.model_copy(update={"timeout": timeout})

    def with_model_hosting_zone(self, model_hosting_zone: ProviderCarbonFootprintZone) -> "Provider":
        return self.model_copy(update={"model_hosting_zone": model_hosting_zone})

    def with_model_total_params(self, model_total_params: int) -> "Provider":
        return self.model_copy(update={"model_total_params": model_total_params})

    def with_model_active_params(self, model_active_params: int) -> "Provider":
        return self.model_copy(update={"model_active_params": model_active_params})

    def with_qos_metric(self, qos_metric: Metric | None) -> "Provider":
        return self.model_copy(update={"qos_metric": qos_metric})

    def with_qos_limit(self, qos_limit: float | None) -> "Provider":
        return self.model_copy(update={"qos_limit": qos_limit})

    def is_compatible_with(self, router: Router) -> bool:
        return self.type.is_compatible_with(router.type)
