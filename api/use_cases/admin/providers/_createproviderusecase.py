from dataclasses import dataclass

from api.domain.model import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider import InvalidProviderTypeError, ProviderGateway, ProviderNotReachableError, ProviderRepository
from api.domain.provider.entities import Provider, ProviderCarbonFootprintZone, ProviderType
from api.domain.provider.errors import ProviderAlreadyExistsError
from api.domain.router import RouterRepository
from api.domain.router.errors import RouterNotFoundError
from api.domain.userinfo import UserInfoRepository
from api.infrastructure.fastapi.schemas.models import ModelType
from api.schemas.core.models import Metric


@dataclass
class CreateProviderUseCaseSuccess:
    provider: Provider


type CreateProviderUseCaseResult = (
    CreateProviderUseCaseSuccess
    | InvalidProviderTypeError
    | ProviderNotReachableError
    | InconsistentModelMaxContextLengthError
    | InconsistentModelVectorSizeError
    | RouterNotFoundError
    | ProviderAlreadyExistsError
)

MODEL_TYPE_TO_MODEL_PROVIDER_TYPE_MAPPING = {
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


class CreateProviderUseCase:
    def __init__(
        self,
        router_repository: RouterRepository,
        provider_repository: ProviderRepository,
        user_info_repository: UserInfoRepository,
        provider_gateway: ProviderGateway,
    ):
        self.router_repository = router_repository
        self.provider_repository = provider_repository
        self.user_info_repository = user_info_repository
        self.provider_gateway = provider_gateway

    async def execute(
        self,
        router_id: int,
        user_id: int,
        provider_type: ProviderType,
        url: str,
        key: str | None,
        timeout: int,
        model_name: str,
        model_hosting_zone: ProviderCarbonFootprintZone,
        model_total_params: int,
        model_active_params: int,
        qos_metric: Metric | None,
        qos_limit: float | None,
    ) -> CreateProviderUseCaseResult:
        router = await self.router_repository.get_router_by_id(router_id=router_id)
        if router is None:
            return RouterNotFoundError(router_id)

        if provider_type.value not in MODEL_TYPE_TO_MODEL_PROVIDER_TYPE_MAPPING[router.type]:
            return InvalidProviderTypeError(provider_type=provider_type.value, router_type=router.type)

        result = await self.provider_gateway.get_capabilities(provider_type=provider_type, url=url, key=key, timeout=timeout, model_name=model_name)

        match result:
            case ProviderNotReachableError() as error:
                return error
            case provider_capabilities:
                pass

        max_context_length = provider_capabilities.max_context_length
        if router.type == ModelType.TEXT_EMBEDDINGS_INFERENCE:
            vector_size = provider_capabilities.vector_size
        else:
            vector_size = None

        if router.providers > 0:
            if router.vector_size != vector_size:
                return InconsistentModelVectorSizeError(
                    actual_vector_size=vector_size, expected_vector_size=router.vector_size, router_name=router.name
                )
            if router.max_context_length != max_context_length:
                return InconsistentModelMaxContextLengthError(
                    actual_max_context_length=max_context_length, expected_max_context_length=router.max_context_length, router_name=router.name
                )

        result = await self.provider_repository.create_provider(
            router_id=router_id,
            user_id=user_id,
            provider_type=provider_type,
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            model_hosting_zone=model_hosting_zone,
            model_total_params=model_total_params,
            model_active_params=model_active_params,
            qos_metric=qos_metric,
            qos_limit=qos_limit,
            max_context_length=max_context_length,
            vector_size=vector_size,
        )

        match result:
            case Provider() as provider:
                return CreateProviderUseCaseSuccess(provider)
            case error:
                return error
