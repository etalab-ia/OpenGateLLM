from api.domain.embeddings.entities import CreateEmbeddingsBody, Embeddings
from api.domain.model.entities import ModelType as RouterType
from api.use_cases._forwarding import ForwardingCommand, ForwardingUseCase, ForwardingUseCaseSuccess
from api.utils.variables import EndpointRoute


class CreateEmbeddingsCommand(CreateEmbeddingsBody, ForwardingCommand): ...


CreateEmbeddingsUseCaseSuccess = ForwardingUseCaseSuccess


class CreateEmbeddingsUseCase(ForwardingUseCase[CreateEmbeddingsCommand, Embeddings]):
    ROUTER_TYPE = RouterType.TEXT_EMBEDDINGS_INFERENCE
    ENDPOINT = EndpointRoute.EMBEDDINGS
    BODY_TYPE = CreateEmbeddingsBody
