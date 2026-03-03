from api.infrastructure.http.model._modelhttpclient import ModelHttpClient, ModelHttpClientEndpoints


class OpenaiModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(ocr=None, rerank=None)
