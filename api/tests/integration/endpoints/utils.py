from urllib.parse import urljoin

import factory
import httpx

from api.domain.provider.entities import ProviderType

DEFAULT_PROVIDER_URL = "http://my-test-provider/"

MODELS_ENDPOINT_BY_PROVIDER = {
    ProviderType.ALBERT: "/v1/models",
    ProviderType.MISTRAL: "/v1/models",
    ProviderType.OPENAI: "/v1/models",
    ProviderType.TEI: "/info",
    ProviderType.VLLM: "/v1/models",
}
METRICS_ENDPOINT_BY_PROVIDER = {
    ProviderType.VLLM: "/metrics",
    ProviderType.MISTRAL: "/metrics",
}
EMBEDDINGS_ENDPOINT_BY_PROVIDER = {
    ProviderType.ALBERT: "/v1/embeddings",
    ProviderType.MISTRAL: "/v1/embeddings",
    ProviderType.OPENAI: "/v1/embeddings",
    ProviderType.TEI: "/v1/embeddings",
    ProviderType.VLLM: "/v1/embeddings",
}
RERANK_ENDPOINT_BY_PROVIDER = {
    ProviderType.TEI: "/rerank",
    ProviderType.VLLM: "/v2/rerank",
}


def mock_models_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int) -> None:
    url = urljoin(DEFAULT_PROVIDER_URL, MODELS_ENDPOINT_BY_PROVIDER[provider_type])
    respx_mock.get(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_embeddings_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int):
    url = urljoin(DEFAULT_PROVIDER_URL, url=EMBEDDINGS_ENDPOINT_BY_PROVIDER[provider_type])
    return respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_rerank_responses(respx_mock, provider_type: ProviderType, body: list | factory.Factory, status_code: int):
    url = urljoin(DEFAULT_PROVIDER_URL, RERANK_ENDPOINT_BY_PROVIDER[provider_type])
    return respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_metrics_responses(respx_mock, provider_type: ProviderType, text: str, status_code: int) -> None:
    url = urljoin(DEFAULT_PROVIDER_URL, METRICS_ENDPOINT_BY_PROVIDER[provider_type])
    respx_mock.get(url=url).mock(return_value=httpx.Response(status_code=status_code, text=text, headers={"Content-Type": "text/plain"}))
