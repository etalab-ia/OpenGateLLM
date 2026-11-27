import asyncio
from collections.abc import Callable

import httpx2
import huggingface_hub
import huggingface_hub.utils._http as hf_http
import pytest
from tokenizers import Tokenizer, models

from api.domain.provider.errors import TokenizerNotLoadableError
from api.infrastructure.huggingface import HuggingFaceTokenizerRegistry

TOKENIZER_JSON = Tokenizer(models.WordLevel({"a": 0}, unk_token="a")).to_str().encode()


def _tokenizer_response() -> httpx2.Response:
    headers = {"ETag": '"abc"', "X-Repo-Commit": "a" * 40, "Content-Length": str(len(TOKENIZER_JSON))}
    return httpx2.Response(200, headers=headers, content=TOKENIZER_JSON)


def _error(status: int, code: str) -> httpx2.Response:
    return httpx2.Response(status, headers={"X-Error-Code": code})


@pytest.fixture
def mock_hub(monkeypatch, tmp_path):
    responses: dict[str, httpx2.Response | Callable[[httpx2.Request], httpx2.Response]] = {}
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        for suffix, response in responses.items():
            if request.url.path.endswith(suffix):
                if callable(response):
                    return response(request)
                if request.method == "HEAD":
                    return httpx2.Response(response.status_code, headers=response.headers)
                return response
        return _error(404, "EntryNotFound")

    client_factory = lambda: httpx2.Client(  # noqa: E731
        event_hooks={"request": [hf_http.hf_request_event_hook]},
        transport=httpx2.MockTransport(handler),
    )
    monkeypatch.setattr(huggingface_hub.constants, "HF_HUB_CACHE", str(tmp_path))
    monkeypatch.setattr(huggingface_hub.constants, "HF_HUB_OFFLINE", False)
    monkeypatch.setattr(huggingface_hub.constants, "HF_HUB_DISABLE_IMPLICIT_TOKEN", True)
    hf_http.set_client_factory(client_factory)
    yield responses, requests
    hf_http.set_client_factory(hf_http.default_client_factory)


def _serve_tokenizer(responses: dict, repo: str) -> None:
    responses[f"/{repo}/resolve/main/tokenizer.json"] = _tokenizer_response()


def _serve_gated_tokenizer(responses: dict, repo: str) -> None:
    responses[f"/{repo}/resolve/main/tokenizer.json"] = lambda request: (
        _tokenizer_response() if "authorization" in request.headers else _error(401, "GatedRepo")
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_the_tokenizer_when_it_is_on_the_hub(mock_hub):
    responses, requests = mock_hub
    _serve_tokenizer(responses, "org/tok")
    registry = HuggingFaceTokenizerRegistry()

    result = await registry.get("org/tok", hf_token="hf_test")

    assert isinstance(result, Tokenizer)
    tokenizer_requests = [r for r in requests if r.url.path.endswith("/tokenizer.json")]
    assert tokenizer_requests[0].headers["Authorization"] == "Bearer hf_test"


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_an_error_when_a_gated_tokenizer_was_cached_with_another_token(mock_hub):
    responses, _ = mock_hub
    _serve_gated_tokenizer(responses, "org/gated")
    registry = HuggingFaceTokenizerRegistry()
    assert isinstance(await registry.get("org/gated", hf_token="hf_ok"), Tokenizer)

    result = await registry.get("org/gated", hf_token=None)

    assert result == TokenizerNotLoadableError(tokenizer_name="org/gated", detail="GatedRepoError")


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_the_cached_tokenizer_without_any_hub_request_when_it_was_already_loaded(mock_hub):
    responses, requests = mock_hub
    _serve_tokenizer(responses, "org/tok")
    registry = HuggingFaceTokenizerRegistry()
    first = await registry.get("org/tok", hf_token=None)
    count = len(requests)

    second = await registry.get("org/tok", hf_token=None)

    assert second is first
    assert len(requests) == count


@pytest.mark.asyncio(loop_scope="session")
async def test_should_load_the_tokenizer_once_when_two_first_loads_run_concurrently(mock_hub):
    responses, requests = mock_hub
    _serve_tokenizer(responses, "org/tok")
    registry = HuggingFaceTokenizerRegistry()

    first, second = await asyncio.gather(registry.get("org/tok", hf_token=None), registry.get("org/tok", hf_token=None))

    assert first is second
    assert len([r for r in requests if r.url.path.endswith("/tokenizer.json") and r.method == "GET"]) == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_should_retry_the_load_when_the_previous_load_failed(mock_hub):
    responses, requests = mock_hub
    responses["/org/tok/resolve/main/tokenizer.json"] = _error(404, "RepoNotFound")
    registry = HuggingFaceTokenizerRegistry()
    first = await registry.get("org/tok", hf_token=None)
    count = len(requests)

    _serve_tokenizer(responses, "org/tok")
    second = await registry.get("org/tok", hf_token=None)

    assert isinstance(first, TokenizerNotLoadableError)
    assert isinstance(second, Tokenizer)
    assert len(requests) > count


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_an_error_when_the_repository_does_not_exist(mock_hub):
    responses, _ = mock_hub
    responses["/org/missing/resolve/main/tokenizer.json"] = _error(404, "RepoNotFound")
    registry = HuggingFaceTokenizerRegistry()

    result = await registry.get("org/missing", hf_token=None)

    assert result == TokenizerNotLoadableError(tokenizer_name="org/missing", detail="RepositoryNotFoundError")


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_an_error_when_the_repository_is_gated(mock_hub):
    responses, _ = mock_hub
    _serve_gated_tokenizer(responses, "org/gated")
    registry = HuggingFaceTokenizerRegistry()

    result = await registry.get("org/gated", hf_token=None)

    assert result == TokenizerNotLoadableError(tokenizer_name="org/gated", detail="GatedRepoError")


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_an_error_when_the_repository_has_no_tokenizer_file(mock_hub):
    responses, _ = mock_hub
    responses["/org/opt/resolve/main/tokenizer.json"] = _error(404, "EntryNotFound")
    registry = HuggingFaceTokenizerRegistry()

    result = await registry.get("org/opt", hf_token=None)

    assert result == TokenizerNotLoadableError(tokenizer_name="org/opt", detail="RemoteEntryNotFoundError")


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_an_error_when_the_name_is_not_a_hub_repository_id(mock_hub):
    responses, requests = mock_hub
    registry = HuggingFaceTokenizerRegistry()

    result = await registry.get("gemma3:1b", hf_token=None)

    assert result == TokenizerNotLoadableError(tokenizer_name="gemma3:1b", detail="HFValidationError")
    assert requests == []


@pytest.mark.asyncio(loop_scope="session")
async def test_should_load_the_tokenizer_from_the_disk_cache_when_the_hub_is_offline(mock_hub, monkeypatch):
    responses, _ = mock_hub
    _serve_tokenizer(responses, "org/tok")
    assert isinstance(await HuggingFaceTokenizerRegistry().get("org/tok", hf_token=None), Tokenizer)
    monkeypatch.setattr(huggingface_hub.constants, "HF_HUB_OFFLINE", True)
    responses.clear()

    result = await HuggingFaceTokenizerRegistry().get("org/tok", hf_token=None)

    assert isinstance(result, Tokenizer)


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_an_error_when_the_hub_is_offline_and_the_tokenizer_is_not_cached(mock_hub, monkeypatch):
    monkeypatch.setattr(huggingface_hub.constants, "HF_HUB_OFFLINE", True)
    registry = HuggingFaceTokenizerRegistry()

    result = await registry.get("org/never-cached", hf_token=None)

    assert result == TokenizerNotLoadableError(tokenizer_name="org/never-cached", detail="LocalEntryNotFoundError")


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_an_error_when_the_hub_rejects_the_token(mock_hub):
    responses, _ = mock_hub
    responses["/org/tok/resolve/main/tokenizer.json"] = httpx2.Response(
        401, headers={"X-Error-Message": "Invalid credentials in Authorization header"}
    )
    registry = HuggingFaceTokenizerRegistry()

    result = await registry.get("org/tok", hf_token="hf_expired")

    assert isinstance(result, TokenizerNotLoadableError)
    assert result.tokenizer_name == "org/tok"
    assert "hf_expired" not in str(result)


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_an_error_when_the_hub_answers_forbidden(mock_hub):
    responses, _ = mock_hub
    responses["/org/tok/resolve/main/tokenizer.json"] = httpx2.Response(403)
    registry = HuggingFaceTokenizerRegistry()

    result = await registry.get("org/tok", hf_token=None)

    assert result == TokenizerNotLoadableError(tokenizer_name="org/tok", detail="HfHubHTTPError")


@pytest.mark.asyncio(loop_scope="session")
async def test_should_return_an_error_and_not_cache_it_when_the_tokenizer_file_is_not_a_tokenizer(mock_hub):
    responses, _ = mock_hub
    malformed = b'{"this is not": "a tokenizer"}'
    responses["/org/bad/resolve/main/tokenizer.json"] = httpx2.Response(
        200, headers={"ETag": '"bad"', "X-Repo-Commit": "a" * 40, "Content-Length": str(len(malformed))}, content=malformed
    )
    registry = HuggingFaceTokenizerRegistry()

    result = await registry.get("org/bad", hf_token=None)

    assert result == TokenizerNotLoadableError(tokenizer_name="org/bad", detail="InvalidTokenizerFile")
    assert registry._tokenizers == {}
