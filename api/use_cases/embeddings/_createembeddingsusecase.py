from api.domain.embeddings.entities import CreateEmbeddingsBody, Embeddings
from api.domain.model.entities import ModelType as RouterType
from api.use_cases._forwarding import ForwardingCommand, ProviderRequestForwardingUseCase, ProviderRequestForwardingUseCaseSuccess
from api.utils.variables import EndpointRoute


class CreateEmbeddingsCommand(ForwardingCommand[CreateEmbeddingsBody]): ...


CreateEmbeddingsUseCaseSuccess = ProviderRequestForwardingUseCaseSuccess


class CreateEmbeddingsUseCase(ProviderRequestForwardingUseCase[CreateEmbeddingsCommand, Embeddings]):
    ROUTER_TYPE = RouterType.TEXT_EMBEDDINGS_INFERENCE
    ENDPOINT = EndpointRoute.EMBEDDINGS
