from api.domain.provider.entities import ProviderType

from ._modelhttpclient import ModelHttpClient, ModelHttpClientEndpoints


class OpenaiModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(ocr=(None, None), rerank=(None, None))
    TYPE = ProviderType.OPENAI
