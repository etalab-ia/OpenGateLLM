# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, Union, Mapping
from typing_extensions import Self, override

import httpx

from . import _exceptions
from ._qs import Querystring
from ._types import (
    NOT_GIVEN,
    Omit,
    Timeout,
    NotGiven,
    Transport,
    ProxiesTypes,
    RequestOptions,
)
from ._utils import (
    is_given,
    get_async_library,
)
from ._version import __version__
from .resources import (
    files,
    chunks,
    health,
    models,
    search,
    documents,
    embeddings,
    collections,
    completions,
    chat_completions,
)
from ._streaming import Stream as Stream, AsyncStream as AsyncStream
from ._exceptions import AlbertAPIError, APIStatusError
from ._base_client import (
    DEFAULT_MAX_RETRIES,
    SyncAPIClient,
    AsyncAPIClient,
)

__all__ = [
    "Timeout",
    "Transport",
    "ProxiesTypes",
    "RequestOptions",
    "AlbertAPI",
    "AsyncAlbertAPI",
    "Client",
    "AsyncClient",
]


class AlbertAPI(SyncAPIClient):
    health: health.HealthResource
    models: models.ModelsResource
    chat_completions: chat_completions.ChatCompletionsResource
    completions: completions.CompletionsResource
    embeddings: embeddings.EmbeddingsResource
    search: search.SearchResource
    collections: collections.CollectionsResource
    files: files.FilesResource
    documents: documents.DocumentsResource
    chunks: chunks.ChunksResource
    with_raw_response: AlbertAPIWithRawResponse
    with_streaming_response: AlbertAPIWithStreamedResponse

    # client options
    api_key: str

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: Union[float, Timeout, None, NotGiven] = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client.
        # We provide a `DefaultHttpxClient` class that you can pass to retain the default values we use for `limits`, `timeout` & `follow_redirects`.
        # See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.Client | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        """Construct a new synchronous albert-api client instance.

        This automatically infers the `api_key` argument from the `API_KEY` environment variable if it is not provided.
        """
        if api_key is None:
            api_key = os.environ.get("API_KEY")
        if api_key is None:
            raise AlbertAPIError(
                "The api_key client option must be set either by passing api_key to the client or by setting the API_KEY environment variable"
            )
        self.api_key = api_key

        if base_url is None:
            base_url = os.environ.get("ALBERT_API_BASE_URL")
        if base_url is None:
            base_url = f"https://localhost:8080/test-api"

        super().__init__(
            version=__version__,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            http_client=http_client,
            custom_headers=default_headers,
            custom_query=default_query,
            _strict_response_validation=_strict_response_validation,
        )

        self.health = health.HealthResource(self)
        self.models = models.ModelsResource(self)
        self.chat_completions = chat_completions.ChatCompletionsResource(self)
        self.completions = completions.CompletionsResource(self)
        self.embeddings = embeddings.EmbeddingsResource(self)
        self.search = search.SearchResource(self)
        self.collections = collections.CollectionsResource(self)
        self.files = files.FilesResource(self)
        self.documents = documents.DocumentsResource(self)
        self.chunks = chunks.ChunksResource(self)
        self.with_raw_response = AlbertAPIWithRawResponse(self)
        self.with_streaming_response = AlbertAPIWithStreamedResponse(self)

    @property
    @override
    def qs(self) -> Querystring:
        return Querystring(array_format="comma")

    @property
    @override
    def auth_headers(self) -> dict[str, str]:
        api_key = self.api_key
        return {"Authorization": f"Bearer {api_key}"}

    @property
    @override
    def default_headers(self) -> dict[str, str | Omit]:
        return {
            **super().default_headers,
            "X-Stainless-Async": "false",
            **self._custom_headers,
        }

    def copy(
        self,
        *,
        api_key: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        http_client = http_client or self._client
        return self.__class__(
            api_key=api_key or self.api_key,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy

    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=body)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=body)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=body)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=body)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=body)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=body)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=body)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=body)
        return APIStatusError(err_msg, response=response, body=body)


class AsyncAlbertAPI(AsyncAPIClient):
    health: health.AsyncHealthResource
    models: models.AsyncModelsResource
    chat_completions: chat_completions.AsyncChatCompletionsResource
    completions: completions.AsyncCompletionsResource
    embeddings: embeddings.AsyncEmbeddingsResource
    search: search.AsyncSearchResource
    collections: collections.AsyncCollectionsResource
    files: files.AsyncFilesResource
    documents: documents.AsyncDocumentsResource
    chunks: chunks.AsyncChunksResource
    with_raw_response: AsyncAlbertAPIWithRawResponse
    with_streaming_response: AsyncAlbertAPIWithStreamedResponse

    # client options
    api_key: str

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: Union[float, Timeout, None, NotGiven] = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client.
        # We provide a `DefaultAsyncHttpxClient` class that you can pass to retain the default values we use for `limits`, `timeout` & `follow_redirects`.
        # See the [httpx documentation](https://www.python-httpx.org/api/#asyncclient) for more details.
        http_client: httpx.AsyncClient | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        """Construct a new async albert-api client instance.

        This automatically infers the `api_key` argument from the `API_KEY` environment variable if it is not provided.
        """
        if api_key is None:
            api_key = os.environ.get("API_KEY")
        if api_key is None:
            raise AlbertAPIError(
                "The api_key client option must be set either by passing api_key to the client or by setting the API_KEY environment variable"
            )
        self.api_key = api_key

        if base_url is None:
            base_url = os.environ.get("ALBERT_API_BASE_URL")
        if base_url is None:
            base_url = f"https://localhost:8080/test-api"

        super().__init__(
            version=__version__,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            http_client=http_client,
            custom_headers=default_headers,
            custom_query=default_query,
            _strict_response_validation=_strict_response_validation,
        )

        self.health = health.AsyncHealthResource(self)
        self.models = models.AsyncModelsResource(self)
        self.chat_completions = chat_completions.AsyncChatCompletionsResource(self)
        self.completions = completions.AsyncCompletionsResource(self)
        self.embeddings = embeddings.AsyncEmbeddingsResource(self)
        self.search = search.AsyncSearchResource(self)
        self.collections = collections.AsyncCollectionsResource(self)
        self.files = files.AsyncFilesResource(self)
        self.documents = documents.AsyncDocumentsResource(self)
        self.chunks = chunks.AsyncChunksResource(self)
        self.with_raw_response = AsyncAlbertAPIWithRawResponse(self)
        self.with_streaming_response = AsyncAlbertAPIWithStreamedResponse(self)

    @property
    @override
    def qs(self) -> Querystring:
        return Querystring(array_format="comma")

    @property
    @override
    def auth_headers(self) -> dict[str, str]:
        api_key = self.api_key
        return {"Authorization": f"Bearer {api_key}"}

    @property
    @override
    def default_headers(self) -> dict[str, str | Omit]:
        return {
            **super().default_headers,
            "X-Stainless-Async": f"async:{get_async_library()}",
            **self._custom_headers,
        }

    def copy(
        self,
        *,
        api_key: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        http_client = http_client or self._client
        return self.__class__(
            api_key=api_key or self.api_key,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy

    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=body)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=body)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=body)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=body)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=body)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=body)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=body)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=body)
        return APIStatusError(err_msg, response=response, body=body)


class AlbertAPIWithRawResponse:
    def __init__(self, client: AlbertAPI) -> None:
        self.health = health.HealthResourceWithRawResponse(client.health)
        self.models = models.ModelsResourceWithRawResponse(client.models)
        self.chat_completions = chat_completions.ChatCompletionsResourceWithRawResponse(client.chat_completions)
        self.completions = completions.CompletionsResourceWithRawResponse(client.completions)
        self.embeddings = embeddings.EmbeddingsResourceWithRawResponse(client.embeddings)
        self.search = search.SearchResourceWithRawResponse(client.search)
        self.collections = collections.CollectionsResourceWithRawResponse(client.collections)
        self.files = files.FilesResourceWithRawResponse(client.files)
        self.documents = documents.DocumentsResourceWithRawResponse(client.documents)
        self.chunks = chunks.ChunksResourceWithRawResponse(client.chunks)


class AsyncAlbertAPIWithRawResponse:
    def __init__(self, client: AsyncAlbertAPI) -> None:
        self.health = health.AsyncHealthResourceWithRawResponse(client.health)
        self.models = models.AsyncModelsResourceWithRawResponse(client.models)
        self.chat_completions = chat_completions.AsyncChatCompletionsResourceWithRawResponse(client.chat_completions)
        self.completions = completions.AsyncCompletionsResourceWithRawResponse(client.completions)
        self.embeddings = embeddings.AsyncEmbeddingsResourceWithRawResponse(client.embeddings)
        self.search = search.AsyncSearchResourceWithRawResponse(client.search)
        self.collections = collections.AsyncCollectionsResourceWithRawResponse(client.collections)
        self.files = files.AsyncFilesResourceWithRawResponse(client.files)
        self.documents = documents.AsyncDocumentsResourceWithRawResponse(client.documents)
        self.chunks = chunks.AsyncChunksResourceWithRawResponse(client.chunks)


class AlbertAPIWithStreamedResponse:
    def __init__(self, client: AlbertAPI) -> None:
        self.health = health.HealthResourceWithStreamingResponse(client.health)
        self.models = models.ModelsResourceWithStreamingResponse(client.models)
        self.chat_completions = chat_completions.ChatCompletionsResourceWithStreamingResponse(client.chat_completions)
        self.completions = completions.CompletionsResourceWithStreamingResponse(client.completions)
        self.embeddings = embeddings.EmbeddingsResourceWithStreamingResponse(client.embeddings)
        self.search = search.SearchResourceWithStreamingResponse(client.search)
        self.collections = collections.CollectionsResourceWithStreamingResponse(client.collections)
        self.files = files.FilesResourceWithStreamingResponse(client.files)
        self.documents = documents.DocumentsResourceWithStreamingResponse(client.documents)
        self.chunks = chunks.ChunksResourceWithStreamingResponse(client.chunks)


class AsyncAlbertAPIWithStreamedResponse:
    def __init__(self, client: AsyncAlbertAPI) -> None:
        self.health = health.AsyncHealthResourceWithStreamingResponse(client.health)
        self.models = models.AsyncModelsResourceWithStreamingResponse(client.models)
        self.chat_completions = chat_completions.AsyncChatCompletionsResourceWithStreamingResponse(
            client.chat_completions
        )
        self.completions = completions.AsyncCompletionsResourceWithStreamingResponse(client.completions)
        self.embeddings = embeddings.AsyncEmbeddingsResourceWithStreamingResponse(client.embeddings)
        self.search = search.AsyncSearchResourceWithStreamingResponse(client.search)
        self.collections = collections.AsyncCollectionsResourceWithStreamingResponse(client.collections)
        self.files = files.AsyncFilesResourceWithStreamingResponse(client.files)
        self.documents = documents.AsyncDocumentsResourceWithStreamingResponse(client.documents)
        self.chunks = chunks.AsyncChunksResourceWithStreamingResponse(client.chunks)


Client = AlbertAPI

AsyncClient = AsyncAlbertAPI
