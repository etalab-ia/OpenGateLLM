from api.domain.model.entities import ModelType as RouterType
from api.use_cases.embeddings import CreateEmbeddingsUseCase
from api.utils.variables import EndpointRoute


class TestCreateEmbeddingsUseCase:
    def test_should_use_text_embeddings_inference_router_type(self):
        assert CreateEmbeddingsUseCase.ROUTER_TYPE == RouterType.TEXT_EMBEDDINGS_INFERENCE

    def test_should_use_embeddings_endpoint(self):
        assert CreateEmbeddingsUseCase.ENDPOINT == EndpointRoute.EMBEDDINGS
