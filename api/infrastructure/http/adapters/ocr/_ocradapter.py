from http import HTTPMethod

from api.domain.ocr.entities import OCR
from api.infrastructure.http.adapters._baseadapter import BaseAdapter
from api.utils.variables import EndpointRoute


class OcrAdapter(BaseAdapter):
    SOURCE_ENDPOINT = EndpointRoute.OCR
    TARGET_ENDPOINT_ROUTE = "/v1/ocr"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = OCR
