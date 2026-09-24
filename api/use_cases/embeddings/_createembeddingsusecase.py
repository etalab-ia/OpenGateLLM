from api.domain.embeddings.entities import CreateEmbeddingsBody, Embeddings
from api.domain.provider.entities import ProviderEndpoint
from api.domain.router.entities import RouterType
from api.use_cases._providerrequestforwardingusecase import (
    ForwardingCommand,
    ProviderRequestForwardingUseCase,
    ProviderRequestForwardingUseCaseResult,
    ProviderRequestForwardingUseCaseSuccess,
)


class CreateEmbeddingsCommand(ForwardingCommand[CreateEmbeddingsBody]): ...


CreateEmbeddingsUseCaseSuccess = ProviderRequestForwardingUseCaseSuccess


class CreateEmbeddingsUseCase(ProviderRequestForwardingUseCase[CreateEmbeddingsCommand, ProviderRequestForwardingUseCaseResult[Embeddings]]):
    ROUTER_TYPE = RouterType.TEXT_EMBEDDINGS_INFERENCE
    ENDPOINT = ProviderEndpoint.EMBEDDINGS
