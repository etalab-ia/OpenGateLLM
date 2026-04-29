from api.infrastructure.http.adapters import OcrAdapter, RerankAdapter


class OpenaiOcrAdapter(OcrAdapter):
    TARGET_ENDPOINT_ROUTE = None


class OpenaiRerankAdapter(RerankAdapter):
    TARGET_ENDPOINT_ROUTE = None
