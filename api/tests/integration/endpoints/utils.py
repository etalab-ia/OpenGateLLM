from urllib.parse import urljoin

import factory
import httpx

from api.domain.provider.entities import ProviderType
from api.infrastructure.http.model.albert import AlbertModelHttpClient
from api.infrastructure.http.model.mistral import MistralModelHttpClient
from api.infrastructure.http.model.openai import OpenaiModelHttpClient
from api.infrastructure.http.model.tei import TeiModelHttpClient
from api.infrastructure.http.model.vllm import VllmModelHttpClient

DEFAULT_PROVIDER_URL = "http://my-test-provider/"
ENDPOINT_TABLE = {
    ProviderType.ALBERT: AlbertModelHttpClient.ENDPOINT_TABLE,
    ProviderType.MISTRAL: MistralModelHttpClient.ENDPOINT_TABLE,
    ProviderType.OPENAI: OpenaiModelHttpClient.ENDPOINT_TABLE,
    ProviderType.TEI: TeiModelHttpClient.ENDPOINT_TABLE,
    ProviderType.VLLM: VllmModelHttpClient.ENDPOINT_TABLE,
}


def mock_models_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int) -> None:
    url = urljoin(base=DEFAULT_PROVIDER_URL, url=ENDPOINT_TABLE[provider_type].models[1])
    respx_mock.get(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_embeddings_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int) -> None:
    url = urljoin(base=DEFAULT_PROVIDER_URL, url=ENDPOINT_TABLE[provider_type].embeddings[1])
    respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))
