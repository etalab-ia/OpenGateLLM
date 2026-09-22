from api.domain.provider.entities import ProviderEndpoint
from api.domain.router.entities import RouterType
from api.use_cases.reranks import CreateRerankUseCase


class TestCreateRerankUseCase:
    def test_should_use_text_classification_router_type(self):
        assert CreateRerankUseCase.ROUTER_TYPE == RouterType.TEXT_CLASSIFICATION

    def test_should_use_rerank_endpoint(self):
        assert CreateRerankUseCase.ENDPOINT == ProviderEndpoint.RERANK
