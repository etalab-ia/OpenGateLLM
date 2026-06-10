from api.infrastructure.http.adapters.rerank import RerankAdapter


class VllmRerankAdapter(RerankAdapter):
    TARGET_ENDPOINT_ROUTE = "/v2/rerank"
