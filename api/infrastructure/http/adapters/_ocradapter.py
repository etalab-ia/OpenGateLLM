from http import HTTPMethod

from api.domain.ocr.entities import OCR
from api.utils.variables import EndpointRoute

from ._endpointadapter import EndpointAdapter


class OcrAdapter(EndpointAdapter):
    SOURCE_ENDPOINT = EndpointRoute.OCR
    TARGET_ENDPOINT_ROUTE = "/v1/ocr"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = OCR
