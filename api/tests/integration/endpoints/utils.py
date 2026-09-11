from urllib.parse import urljoin

import factory
import httpx

from api.domain.provider.entities import ProviderType

DEFAULT_PROVIDER_URL = "http://my-test-provider/"

AUDIO_TRANSCRIPTIONS_ENDPOINT_BY_PROVIDER = {
    ProviderType.ALBERT: "/v1/audio/transcriptions",
    ProviderType.OPENAI: "/v1/audio/transcriptions",
    ProviderType.VLLM: "/v1/audio/transcriptions",
    ProviderType.MISTRAL: "/v1/chat/completions",
}
EMBEDDINGS_ENDPOINT_BY_PROVIDER = {
    ProviderType.ALBERT: "/v1/embeddings",
    ProviderType.MISTRAL: "/v1/embeddings",
    ProviderType.OPENAI: "/v1/embeddings",
    ProviderType.TEI: "/v1/embeddings",
    ProviderType.VLLM: "/v1/embeddings",
}
CHAT_COMPLETIONS_ENDPOINT_BY_PROVIDER = {
    ProviderType.ALBERT: "/v1/chat/completions",
    ProviderType.MISTRAL: "/v1/chat/completions",
    ProviderType.OPENAI: "/v1/chat/completions",
    ProviderType.VLLM: "/v1/chat/completions",
}
MODELS_ENDPOINT_BY_PROVIDER = {
    ProviderType.ALBERT: "/v1/models",
    ProviderType.MISTRAL: "/v1/models",
    ProviderType.OPENAI: "/v1/models",
    ProviderType.TEI: "/info",
    ProviderType.VLLM: "/v1/models",
}
OCR_ENDPOINT_BY_PROVIDER = {
    ProviderType.ALBERT: "/v1/ocr",
    ProviderType.MISTRAL: "/v1/ocr",
}

RERANK_ENDPOINT_BY_PROVIDER = {
    ProviderType.TEI: "/rerank",
    ProviderType.VLLM: "/v2/rerank",
}


def mock_models_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int) -> None:
    url = urljoin(DEFAULT_PROVIDER_URL, MODELS_ENDPOINT_BY_PROVIDER[provider_type])
    respx_mock.get(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_chat_completions_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int):
    url = urljoin(DEFAULT_PROVIDER_URL, CHAT_COMPLETIONS_ENDPOINT_BY_PROVIDER[provider_type])
    return respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_chat_completions_stream(respx_mock, provider_type: ProviderType, lines: list[str], status_code: int = 200):
    url = urljoin(DEFAULT_PROVIDER_URL, CHAT_COMPLETIONS_ENDPOINT_BY_PROVIDER[provider_type])
    response = httpx.Response(status_code=status_code, text="\n\n".join(lines), headers={"Content-Type": "text/event-stream"})
    return respx_mock.post(url=url).mock(return_value=response)


def mock_embeddings_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int):
    url = urljoin(DEFAULT_PROVIDER_URL, url=EMBEDDINGS_ENDPOINT_BY_PROVIDER[provider_type])
    return respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_rerank_responses(respx_mock, provider_type: ProviderType, body: list | factory.Factory, status_code: int):
    url = urljoin(DEFAULT_PROVIDER_URL, RERANK_ENDPOINT_BY_PROVIDER[provider_type])
    return respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_ocr_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int) -> None:
    url = urljoin(DEFAULT_PROVIDER_URL, OCR_ENDPOINT_BY_PROVIDER[provider_type])
    respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_audio_transcriptions_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int):
    url = urljoin(DEFAULT_PROVIDER_URL, AUDIO_TRANSCRIPTIONS_ENDPOINT_BY_PROVIDER[provider_type])
    return respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))
