from api.domain.provider.entities import ProviderType
from api.infrastructure.http.model import ModelHttpClient, ModelHttpClientEndpoints


class OpenaiModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(ocr=(None, None), rerank=(None, None))
    TYPE = ProviderType.OPENAI
