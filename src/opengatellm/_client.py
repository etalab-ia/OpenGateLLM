# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Mapping
from typing_extensions import Self, override

import httpx

from . import _exceptions
from ._qs import Querystring
from ._types import (
    Omit,
    Timeout,
    NotGiven,
    Transport,
    ProxiesTypes,
    RequestOptions,
    not_given,
)
from ._utils import is_given, get_async_library
from ._compat import cached_property
from ._version import __version__
from ._streaming import Stream as Stream, AsyncStream as AsyncStream
from ._exceptions import APIStatusError, OpengatellmError
from ._base_client import (
    DEFAULT_MAX_RETRIES,
    SyncAPIClient,
    AsyncAPIClient,
)

if TYPE_CHECKING:
    from .resources import (
        me,
        ocr,
        auth,
        chat,
        admin,
        audio,
        chunks,
        health,
        models,
        rerank,
        search,
        metrics,
        documents,
        embeddings,
        parse_beta,
        collections,
    )
    from .resources.ocr import OcrResource, AsyncOcrResource
    from .resources.auth import AuthResource, AsyncAuthResource
    from .resources.chat import ChatResource, AsyncChatResource
    from .resources.audio import AudioResource, AsyncAudioResource
    from .resources.me.me import MeResource, AsyncMeResource
    from .resources.chunks import ChunksResource, AsyncChunksResource
    from .resources.health import HealthResource, AsyncHealthResource
    from .resources.models import ModelsResource, AsyncModelsResource
    from .resources.rerank import RerankResource, AsyncRerankResource
    from .resources.search import SearchResource, AsyncSearchResource
    from .resources.metrics import MetricsResource, AsyncMetricsResource
    from .resources.embeddings import EmbeddingsResource, AsyncEmbeddingsResource
    from .resources.parse_beta import ParseBetaResource, AsyncParseBetaResource
    from .resources.admin.admin import AdminResource, AsyncAdminResource
    from .resources.collections import CollectionsResource, AsyncCollectionsResource
    from .resources.documents.documents import DocumentsResource, AsyncDocumentsResource

__all__ = [
    "Timeout",
    "Transport",
    "ProxiesTypes",
    "RequestOptions",
    "Opengatellm",
    "AsyncOpengatellm",
    "Client",
    "AsyncClient",
]


class Opengatellm(SyncAPIClient):
    # client options
    bearer_token: str

    def __init__(
        self,
        *,
        bearer_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = not_given,
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
        """Construct a new synchronous Opengatellm client instance.

        This automatically infers the `bearer_token` argument from the `OPENGATELLM_BEARER_TOKEN` environment variable if it is not provided.
        """
        if bearer_token is None:
            bearer_token = os.environ.get("OPENGATELLM_BEARER_TOKEN")
        if bearer_token is None:
            raise OpengatellmError(
                "The bearer_token client option must be set either by passing bearer_token to the client or by setting the OPENGATELLM_BEARER_TOKEN environment variable"
            )
        self.bearer_token = bearer_token

        if base_url is None:
            base_url = os.environ.get("OPENGATELLM_BASE_URL")
        if base_url is None:
            base_url = f"https://api.example.com"

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

    @cached_property
    def admin(self) -> AdminResource:
        from .resources.admin import AdminResource

        return AdminResource(self)

    @cached_property
    def audio(self) -> AudioResource:
        from .resources.audio import AudioResource

        return AudioResource(self)

    @cached_property
    def auth(self) -> AuthResource:
        from .resources.auth import AuthResource

        return AuthResource(self)

    @cached_property
    def chat(self) -> ChatResource:
        from .resources.chat import ChatResource

        return ChatResource(self)

    @cached_property
    def chunks(self) -> ChunksResource:
        from .resources.chunks import ChunksResource

        return ChunksResource(self)

    @cached_property
    def collections(self) -> CollectionsResource:
        from .resources.collections import CollectionsResource

        return CollectionsResource(self)

    @cached_property
    def documents(self) -> DocumentsResource:
        from .resources.documents import DocumentsResource

        return DocumentsResource(self)

    @cached_property
    def embeddings(self) -> EmbeddingsResource:
        from .resources.embeddings import EmbeddingsResource

        return EmbeddingsResource(self)

    @cached_property
    def me(self) -> MeResource:
        from .resources.me import MeResource

        return MeResource(self)

    @cached_property
    def models(self) -> ModelsResource:
        from .resources.models import ModelsResource

        return ModelsResource(self)

    @cached_property
    def ocr(self) -> OcrResource:
        from .resources.ocr import OcrResource

        return OcrResource(self)

    @cached_property
    def parse_beta(self) -> ParseBetaResource:
        from .resources.parse_beta import ParseBetaResource

        return ParseBetaResource(self)

    @cached_property
    def rerank(self) -> RerankResource:
        from .resources.rerank import RerankResource

        return RerankResource(self)

    @cached_property
    def search(self) -> SearchResource:
        from .resources.search import SearchResource

        return SearchResource(self)

    @cached_property
    def metrics(self) -> MetricsResource:
        from .resources.metrics import MetricsResource

        return MetricsResource(self)

    @cached_property
    def health(self) -> HealthResource:
        from .resources.health import HealthResource

        return HealthResource(self)

    @cached_property
    def with_raw_response(self) -> OpengatellmWithRawResponse:
        return OpengatellmWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> OpengatellmWithStreamedResponse:
        return OpengatellmWithStreamedResponse(self)

    @property
    @override
    def qs(self) -> Querystring:
        return Querystring(array_format="comma")

    @property
    @override
    def auth_headers(self) -> dict[str, str]:
        bearer_token = self.bearer_token
        return {"Authorization": f"Bearer {bearer_token}"}

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
        bearer_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = not_given,
        http_client: httpx.Client | None = None,
        max_retries: int | NotGiven = not_given,
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
            bearer_token=bearer_token or self.bearer_token,
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


class AsyncOpengatellm(AsyncAPIClient):
    # client options
    bearer_token: str

    def __init__(
        self,
        *,
        bearer_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = not_given,
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
        """Construct a new async AsyncOpengatellm client instance.

        This automatically infers the `bearer_token` argument from the `OPENGATELLM_BEARER_TOKEN` environment variable if it is not provided.
        """
        if bearer_token is None:
            bearer_token = os.environ.get("OPENGATELLM_BEARER_TOKEN")
        if bearer_token is None:
            raise OpengatellmError(
                "The bearer_token client option must be set either by passing bearer_token to the client or by setting the OPENGATELLM_BEARER_TOKEN environment variable"
            )
        self.bearer_token = bearer_token

        if base_url is None:
            base_url = os.environ.get("OPENGATELLM_BASE_URL")
        if base_url is None:
            base_url = f"https://api.example.com"

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

    @cached_property
    def admin(self) -> AsyncAdminResource:
        from .resources.admin import AsyncAdminResource

        return AsyncAdminResource(self)

    @cached_property
    def audio(self) -> AsyncAudioResource:
        from .resources.audio import AsyncAudioResource

        return AsyncAudioResource(self)

    @cached_property
    def auth(self) -> AsyncAuthResource:
        from .resources.auth import AsyncAuthResource

        return AsyncAuthResource(self)

    @cached_property
    def chat(self) -> AsyncChatResource:
        from .resources.chat import AsyncChatResource

        return AsyncChatResource(self)

    @cached_property
    def chunks(self) -> AsyncChunksResource:
        from .resources.chunks import AsyncChunksResource

        return AsyncChunksResource(self)

    @cached_property
    def collections(self) -> AsyncCollectionsResource:
        from .resources.collections import AsyncCollectionsResource

        return AsyncCollectionsResource(self)

    @cached_property
    def documents(self) -> AsyncDocumentsResource:
        from .resources.documents import AsyncDocumentsResource

        return AsyncDocumentsResource(self)

    @cached_property
    def embeddings(self) -> AsyncEmbeddingsResource:
        from .resources.embeddings import AsyncEmbeddingsResource

        return AsyncEmbeddingsResource(self)

    @cached_property
    def me(self) -> AsyncMeResource:
        from .resources.me import AsyncMeResource

        return AsyncMeResource(self)

    @cached_property
    def models(self) -> AsyncModelsResource:
        from .resources.models import AsyncModelsResource

        return AsyncModelsResource(self)

    @cached_property
    def ocr(self) -> AsyncOcrResource:
        from .resources.ocr import AsyncOcrResource

        return AsyncOcrResource(self)

    @cached_property
    def parse_beta(self) -> AsyncParseBetaResource:
        from .resources.parse_beta import AsyncParseBetaResource

        return AsyncParseBetaResource(self)

    @cached_property
    def rerank(self) -> AsyncRerankResource:
        from .resources.rerank import AsyncRerankResource

        return AsyncRerankResource(self)

    @cached_property
    def search(self) -> AsyncSearchResource:
        from .resources.search import AsyncSearchResource

        return AsyncSearchResource(self)

    @cached_property
    def metrics(self) -> AsyncMetricsResource:
        from .resources.metrics import AsyncMetricsResource

        return AsyncMetricsResource(self)

    @cached_property
    def health(self) -> AsyncHealthResource:
        from .resources.health import AsyncHealthResource

        return AsyncHealthResource(self)

    @cached_property
    def with_raw_response(self) -> AsyncOpengatellmWithRawResponse:
        return AsyncOpengatellmWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncOpengatellmWithStreamedResponse:
        return AsyncOpengatellmWithStreamedResponse(self)

    @property
    @override
    def qs(self) -> Querystring:
        return Querystring(array_format="comma")

    @property
    @override
    def auth_headers(self) -> dict[str, str]:
        bearer_token = self.bearer_token
        return {"Authorization": f"Bearer {bearer_token}"}

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
        bearer_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = not_given,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int | NotGiven = not_given,
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
            bearer_token=bearer_token or self.bearer_token,
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


class OpengatellmWithRawResponse:
    _client: Opengatellm

    def __init__(self, client: Opengatellm) -> None:
        self._client = client

    @cached_property
    def admin(self) -> admin.AdminResourceWithRawResponse:
        from .resources.admin import AdminResourceWithRawResponse

        return AdminResourceWithRawResponse(self._client.admin)

    @cached_property
    def audio(self) -> audio.AudioResourceWithRawResponse:
        from .resources.audio import AudioResourceWithRawResponse

        return AudioResourceWithRawResponse(self._client.audio)

    @cached_property
    def auth(self) -> auth.AuthResourceWithRawResponse:
        from .resources.auth import AuthResourceWithRawResponse

        return AuthResourceWithRawResponse(self._client.auth)

    @cached_property
    def chat(self) -> chat.ChatResourceWithRawResponse:
        from .resources.chat import ChatResourceWithRawResponse

        return ChatResourceWithRawResponse(self._client.chat)

    @cached_property
    def chunks(self) -> chunks.ChunksResourceWithRawResponse:
        from .resources.chunks import ChunksResourceWithRawResponse

        return ChunksResourceWithRawResponse(self._client.chunks)

    @cached_property
    def collections(self) -> collections.CollectionsResourceWithRawResponse:
        from .resources.collections import CollectionsResourceWithRawResponse

        return CollectionsResourceWithRawResponse(self._client.collections)

    @cached_property
    def documents(self) -> documents.DocumentsResourceWithRawResponse:
        from .resources.documents import DocumentsResourceWithRawResponse

        return DocumentsResourceWithRawResponse(self._client.documents)

    @cached_property
    def embeddings(self) -> embeddings.EmbeddingsResourceWithRawResponse:
        from .resources.embeddings import EmbeddingsResourceWithRawResponse

        return EmbeddingsResourceWithRawResponse(self._client.embeddings)

    @cached_property
    def me(self) -> me.MeResourceWithRawResponse:
        from .resources.me import MeResourceWithRawResponse

        return MeResourceWithRawResponse(self._client.me)

    @cached_property
    def models(self) -> models.ModelsResourceWithRawResponse:
        from .resources.models import ModelsResourceWithRawResponse

        return ModelsResourceWithRawResponse(self._client.models)

    @cached_property
    def ocr(self) -> ocr.OcrResourceWithRawResponse:
        from .resources.ocr import OcrResourceWithRawResponse

        return OcrResourceWithRawResponse(self._client.ocr)

    @cached_property
    def parse_beta(self) -> parse_beta.ParseBetaResourceWithRawResponse:
        from .resources.parse_beta import ParseBetaResourceWithRawResponse

        return ParseBetaResourceWithRawResponse(self._client.parse_beta)

    @cached_property
    def rerank(self) -> rerank.RerankResourceWithRawResponse:
        from .resources.rerank import RerankResourceWithRawResponse

        return RerankResourceWithRawResponse(self._client.rerank)

    @cached_property
    def search(self) -> search.SearchResourceWithRawResponse:
        from .resources.search import SearchResourceWithRawResponse

        return SearchResourceWithRawResponse(self._client.search)

    @cached_property
    def metrics(self) -> metrics.MetricsResourceWithRawResponse:
        from .resources.metrics import MetricsResourceWithRawResponse

        return MetricsResourceWithRawResponse(self._client.metrics)

    @cached_property
    def health(self) -> health.HealthResourceWithRawResponse:
        from .resources.health import HealthResourceWithRawResponse

        return HealthResourceWithRawResponse(self._client.health)


class AsyncOpengatellmWithRawResponse:
    _client: AsyncOpengatellm

    def __init__(self, client: AsyncOpengatellm) -> None:
        self._client = client

    @cached_property
    def admin(self) -> admin.AsyncAdminResourceWithRawResponse:
        from .resources.admin import AsyncAdminResourceWithRawResponse

        return AsyncAdminResourceWithRawResponse(self._client.admin)

    @cached_property
    def audio(self) -> audio.AsyncAudioResourceWithRawResponse:
        from .resources.audio import AsyncAudioResourceWithRawResponse

        return AsyncAudioResourceWithRawResponse(self._client.audio)

    @cached_property
    def auth(self) -> auth.AsyncAuthResourceWithRawResponse:
        from .resources.auth import AsyncAuthResourceWithRawResponse

        return AsyncAuthResourceWithRawResponse(self._client.auth)

    @cached_property
    def chat(self) -> chat.AsyncChatResourceWithRawResponse:
        from .resources.chat import AsyncChatResourceWithRawResponse

        return AsyncChatResourceWithRawResponse(self._client.chat)

    @cached_property
    def chunks(self) -> chunks.AsyncChunksResourceWithRawResponse:
        from .resources.chunks import AsyncChunksResourceWithRawResponse

        return AsyncChunksResourceWithRawResponse(self._client.chunks)

    @cached_property
    def collections(self) -> collections.AsyncCollectionsResourceWithRawResponse:
        from .resources.collections import AsyncCollectionsResourceWithRawResponse

        return AsyncCollectionsResourceWithRawResponse(self._client.collections)

    @cached_property
    def documents(self) -> documents.AsyncDocumentsResourceWithRawResponse:
        from .resources.documents import AsyncDocumentsResourceWithRawResponse

        return AsyncDocumentsResourceWithRawResponse(self._client.documents)

    @cached_property
    def embeddings(self) -> embeddings.AsyncEmbeddingsResourceWithRawResponse:
        from .resources.embeddings import AsyncEmbeddingsResourceWithRawResponse

        return AsyncEmbeddingsResourceWithRawResponse(self._client.embeddings)

    @cached_property
    def me(self) -> me.AsyncMeResourceWithRawResponse:
        from .resources.me import AsyncMeResourceWithRawResponse

        return AsyncMeResourceWithRawResponse(self._client.me)

    @cached_property
    def models(self) -> models.AsyncModelsResourceWithRawResponse:
        from .resources.models import AsyncModelsResourceWithRawResponse

        return AsyncModelsResourceWithRawResponse(self._client.models)

    @cached_property
    def ocr(self) -> ocr.AsyncOcrResourceWithRawResponse:
        from .resources.ocr import AsyncOcrResourceWithRawResponse

        return AsyncOcrResourceWithRawResponse(self._client.ocr)

    @cached_property
    def parse_beta(self) -> parse_beta.AsyncParseBetaResourceWithRawResponse:
        from .resources.parse_beta import AsyncParseBetaResourceWithRawResponse

        return AsyncParseBetaResourceWithRawResponse(self._client.parse_beta)

    @cached_property
    def rerank(self) -> rerank.AsyncRerankResourceWithRawResponse:
        from .resources.rerank import AsyncRerankResourceWithRawResponse

        return AsyncRerankResourceWithRawResponse(self._client.rerank)

    @cached_property
    def search(self) -> search.AsyncSearchResourceWithRawResponse:
        from .resources.search import AsyncSearchResourceWithRawResponse

        return AsyncSearchResourceWithRawResponse(self._client.search)

    @cached_property
    def metrics(self) -> metrics.AsyncMetricsResourceWithRawResponse:
        from .resources.metrics import AsyncMetricsResourceWithRawResponse

        return AsyncMetricsResourceWithRawResponse(self._client.metrics)

    @cached_property
    def health(self) -> health.AsyncHealthResourceWithRawResponse:
        from .resources.health import AsyncHealthResourceWithRawResponse

        return AsyncHealthResourceWithRawResponse(self._client.health)


class OpengatellmWithStreamedResponse:
    _client: Opengatellm

    def __init__(self, client: Opengatellm) -> None:
        self._client = client

    @cached_property
    def admin(self) -> admin.AdminResourceWithStreamingResponse:
        from .resources.admin import AdminResourceWithStreamingResponse

        return AdminResourceWithStreamingResponse(self._client.admin)

    @cached_property
    def audio(self) -> audio.AudioResourceWithStreamingResponse:
        from .resources.audio import AudioResourceWithStreamingResponse

        return AudioResourceWithStreamingResponse(self._client.audio)

    @cached_property
    def auth(self) -> auth.AuthResourceWithStreamingResponse:
        from .resources.auth import AuthResourceWithStreamingResponse

        return AuthResourceWithStreamingResponse(self._client.auth)

    @cached_property
    def chat(self) -> chat.ChatResourceWithStreamingResponse:
        from .resources.chat import ChatResourceWithStreamingResponse

        return ChatResourceWithStreamingResponse(self._client.chat)

    @cached_property
    def chunks(self) -> chunks.ChunksResourceWithStreamingResponse:
        from .resources.chunks import ChunksResourceWithStreamingResponse

        return ChunksResourceWithStreamingResponse(self._client.chunks)

    @cached_property
    def collections(self) -> collections.CollectionsResourceWithStreamingResponse:
        from .resources.collections import CollectionsResourceWithStreamingResponse

        return CollectionsResourceWithStreamingResponse(self._client.collections)

    @cached_property
    def documents(self) -> documents.DocumentsResourceWithStreamingResponse:
        from .resources.documents import DocumentsResourceWithStreamingResponse

        return DocumentsResourceWithStreamingResponse(self._client.documents)

    @cached_property
    def embeddings(self) -> embeddings.EmbeddingsResourceWithStreamingResponse:
        from .resources.embeddings import EmbeddingsResourceWithStreamingResponse

        return EmbeddingsResourceWithStreamingResponse(self._client.embeddings)

    @cached_property
    def me(self) -> me.MeResourceWithStreamingResponse:
        from .resources.me import MeResourceWithStreamingResponse

        return MeResourceWithStreamingResponse(self._client.me)

    @cached_property
    def models(self) -> models.ModelsResourceWithStreamingResponse:
        from .resources.models import ModelsResourceWithStreamingResponse

        return ModelsResourceWithStreamingResponse(self._client.models)

    @cached_property
    def ocr(self) -> ocr.OcrResourceWithStreamingResponse:
        from .resources.ocr import OcrResourceWithStreamingResponse

        return OcrResourceWithStreamingResponse(self._client.ocr)

    @cached_property
    def parse_beta(self) -> parse_beta.ParseBetaResourceWithStreamingResponse:
        from .resources.parse_beta import ParseBetaResourceWithStreamingResponse

        return ParseBetaResourceWithStreamingResponse(self._client.parse_beta)

    @cached_property
    def rerank(self) -> rerank.RerankResourceWithStreamingResponse:
        from .resources.rerank import RerankResourceWithStreamingResponse

        return RerankResourceWithStreamingResponse(self._client.rerank)

    @cached_property
    def search(self) -> search.SearchResourceWithStreamingResponse:
        from .resources.search import SearchResourceWithStreamingResponse

        return SearchResourceWithStreamingResponse(self._client.search)

    @cached_property
    def metrics(self) -> metrics.MetricsResourceWithStreamingResponse:
        from .resources.metrics import MetricsResourceWithStreamingResponse

        return MetricsResourceWithStreamingResponse(self._client.metrics)

    @cached_property
    def health(self) -> health.HealthResourceWithStreamingResponse:
        from .resources.health import HealthResourceWithStreamingResponse

        return HealthResourceWithStreamingResponse(self._client.health)


class AsyncOpengatellmWithStreamedResponse:
    _client: AsyncOpengatellm

    def __init__(self, client: AsyncOpengatellm) -> None:
        self._client = client

    @cached_property
    def admin(self) -> admin.AsyncAdminResourceWithStreamingResponse:
        from .resources.admin import AsyncAdminResourceWithStreamingResponse

        return AsyncAdminResourceWithStreamingResponse(self._client.admin)

    @cached_property
    def audio(self) -> audio.AsyncAudioResourceWithStreamingResponse:
        from .resources.audio import AsyncAudioResourceWithStreamingResponse

        return AsyncAudioResourceWithStreamingResponse(self._client.audio)

    @cached_property
    def auth(self) -> auth.AsyncAuthResourceWithStreamingResponse:
        from .resources.auth import AsyncAuthResourceWithStreamingResponse

        return AsyncAuthResourceWithStreamingResponse(self._client.auth)

    @cached_property
    def chat(self) -> chat.AsyncChatResourceWithStreamingResponse:
        from .resources.chat import AsyncChatResourceWithStreamingResponse

        return AsyncChatResourceWithStreamingResponse(self._client.chat)

    @cached_property
    def chunks(self) -> chunks.AsyncChunksResourceWithStreamingResponse:
        from .resources.chunks import AsyncChunksResourceWithStreamingResponse

        return AsyncChunksResourceWithStreamingResponse(self._client.chunks)

    @cached_property
    def collections(self) -> collections.AsyncCollectionsResourceWithStreamingResponse:
        from .resources.collections import AsyncCollectionsResourceWithStreamingResponse

        return AsyncCollectionsResourceWithStreamingResponse(self._client.collections)

    @cached_property
    def documents(self) -> documents.AsyncDocumentsResourceWithStreamingResponse:
        from .resources.documents import AsyncDocumentsResourceWithStreamingResponse

        return AsyncDocumentsResourceWithStreamingResponse(self._client.documents)

    @cached_property
    def embeddings(self) -> embeddings.AsyncEmbeddingsResourceWithStreamingResponse:
        from .resources.embeddings import AsyncEmbeddingsResourceWithStreamingResponse

        return AsyncEmbeddingsResourceWithStreamingResponse(self._client.embeddings)

    @cached_property
    def me(self) -> me.AsyncMeResourceWithStreamingResponse:
        from .resources.me import AsyncMeResourceWithStreamingResponse

        return AsyncMeResourceWithStreamingResponse(self._client.me)

    @cached_property
    def models(self) -> models.AsyncModelsResourceWithStreamingResponse:
        from .resources.models import AsyncModelsResourceWithStreamingResponse

        return AsyncModelsResourceWithStreamingResponse(self._client.models)

    @cached_property
    def ocr(self) -> ocr.AsyncOcrResourceWithStreamingResponse:
        from .resources.ocr import AsyncOcrResourceWithStreamingResponse

        return AsyncOcrResourceWithStreamingResponse(self._client.ocr)

    @cached_property
    def parse_beta(self) -> parse_beta.AsyncParseBetaResourceWithStreamingResponse:
        from .resources.parse_beta import AsyncParseBetaResourceWithStreamingResponse

        return AsyncParseBetaResourceWithStreamingResponse(self._client.parse_beta)

    @cached_property
    def rerank(self) -> rerank.AsyncRerankResourceWithStreamingResponse:
        from .resources.rerank import AsyncRerankResourceWithStreamingResponse

        return AsyncRerankResourceWithStreamingResponse(self._client.rerank)

    @cached_property
    def search(self) -> search.AsyncSearchResourceWithStreamingResponse:
        from .resources.search import AsyncSearchResourceWithStreamingResponse

        return AsyncSearchResourceWithStreamingResponse(self._client.search)

    @cached_property
    def metrics(self) -> metrics.AsyncMetricsResourceWithStreamingResponse:
        from .resources.metrics import AsyncMetricsResourceWithStreamingResponse

        return AsyncMetricsResourceWithStreamingResponse(self._client.metrics)

    @cached_property
    def health(self) -> health.AsyncHealthResourceWithStreamingResponse:
        from .resources.health import AsyncHealthResourceWithStreamingResponse

        return AsyncHealthResourceWithStreamingResponse(self._client.health)


Client = Opengatellm

AsyncClient = AsyncOpengatellm
