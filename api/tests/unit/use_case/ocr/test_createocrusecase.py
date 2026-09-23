from api.domain.provider.entities import ProviderEndpoint
from api.domain.router.entities import RouterType
from api.use_cases.ocr import CreateOCRUseCase


class TestCreateOCRUseCase:
    def test_should_use_text_embeddings_inference_router_type(self):
        assert CreateOCRUseCase.ROUTER_TYPE == RouterType.IMAGE_TO_TEXT

    def test_should_use_embeddings_endpoint(self):
        assert CreateOCRUseCase.ENDPOINT == ProviderEndpoint.OCR
