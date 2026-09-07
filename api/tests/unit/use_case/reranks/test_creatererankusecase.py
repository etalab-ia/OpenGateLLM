from api.domain.router.entities import RouterType
from api.use_cases.reranks import CreateRerankUseCase
from api.utils.variables import EndpointRoute


class TestCreateRerankUseCase:
    def test_should_use_text_classification_router_type(self):
        assert CreateRerankUseCase.ROUTER_TYPE == RouterType.TEXT_CLASSIFICATION

    def test_should_use_rerank_endpoint(self):
        assert CreateRerankUseCase.ENDPOINT == EndpointRoute.RERANK
