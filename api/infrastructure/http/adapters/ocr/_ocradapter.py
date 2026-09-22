from http import HTTPMethod

from api.domain.ocr.entities import OCR
from api.domain.provider.entities import ProviderEndpoint
from api.infrastructure.http.adapters import HttpProviderAdapter


class OcrAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = ProviderEndpoint.OCR
    TARGET_ENDPOINT_ROUTE = "/v1/ocr"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = OCR
