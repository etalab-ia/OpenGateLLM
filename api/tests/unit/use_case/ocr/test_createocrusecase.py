from api.domain.model.entities import ModelType as RouterType
from api.use_cases.ocr import CreateOCRUseCase
from api.utils.variables import EndpointRoute


class TestCreateOCRUseCase:
    def test_should_use_text_embeddings_inference_router_type(self):
        assert CreateOCRUseCase.ROUTER_TYPE == RouterType.IMAGE_TO_TEXT

    def test_should_use_embeddings_endpoint(self):
        assert CreateOCRUseCase.ENDPOINT == EndpointRoute.OCR
