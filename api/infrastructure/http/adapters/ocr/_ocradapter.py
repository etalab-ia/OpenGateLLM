from http import HTTPMethod

from api.domain.ocr.entities import OCR
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class OcrAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.OCR
    TARGET_ENDPOINT_ROUTE = "/v1/ocr"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = OCR
