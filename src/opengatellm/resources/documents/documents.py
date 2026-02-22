# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Mapping, Optional, cast
from typing_extensions import Literal

import httpx

from .chunks import (
    ChunksResource,
    AsyncChunksResource,
    ChunksResourceWithRawResponse,
    AsyncChunksResourceWithRawResponse,
    ChunksResourceWithStreamingResponse,
    AsyncChunksResourceWithStreamingResponse,
)
from ...types import document_list_params, document_create_params
from ..._types import (
    Body,
    Omit,
    Query,
    Headers,
    NoneType,
    NotGiven,
    FileTypes,
    SequenceNotStr,
    omit,
    not_given,
)
from ..._utils import extract_files, maybe_transform, deepcopy_minimal, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from ..._base_client import make_request_options
from ...types.document_create_response import DocumentCreateResponse
from ...types.document_retrieve_response import DocumentRetrieveResponse

__all__ = ["DocumentsResource", "AsyncDocumentsResource"]


class DocumentsResource(SyncAPIResource):
    @cached_property
    def chunks(self) -> ChunksResource:
        return ChunksResource(self._client)

    @cached_property
    def with_raw_response(self) -> DocumentsResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return DocumentsResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> DocumentsResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return DocumentsResourceWithStreamingResponse(self)

    def create(
        self,
        *,
        chunk_min_size: int | Omit = omit,
        chunk_overlap: int | Omit = omit,
        chunk_size: int | Omit = omit,
        collection: Optional[int] | Omit = omit,
        collection_id: Optional[int] | Omit = omit,
        disable_chunking: bool | Omit = omit,
        file: Optional[FileTypes] | Omit = omit,
        is_separator_regex: bool | Omit = omit,
        metadata: str | Omit = omit,
        name: Optional[str] | Omit = omit,
        preset_separators: Literal[
            "cpp",
            "go",
            "java",
            "kotlin",
            "js",
            "ts",
            "php",
            "proto",
            "python",
            "r",
            "rst",
            "ruby",
            "rust",
            "scala",
            "swift",
            "markdown",
            "latex",
            "html",
            "sol",
            "csharp",
            "cobol",
            "c",
            "lua",
            "perl",
            "haskell",
            "elixir",
            "powershell",
            "visualbasic6",
        ]
        | Omit = omit,
        separators: SequenceNotStr[str] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> DocumentCreateResponse:
        """Upload a file, parse and split it into chunks, then create a document.

        If no
        file is provided, the document will be created without content, use POST
        `/v1/documents/{document_id}/chunks` to fill it.

        Args:
          chunk_min_size: The minimum size in characters of the chunks to use for the upload file.

          chunk_overlap: The overlap in characters of the chunks to use for the upload file.

          chunk_size: The size in characters of the chunks to use for the upload file. If not
              provided, the document will not be split into chunks.

          collection_id: The collection ID to use for the file upload. The file will be vectorized with
              model defined by the collection.

          disable_chunking: Whether to disable `RecursiveCharacterTextSplitter` chunking for the upload
              file.

          file: The file to create a document from. If not provided, the document will be
              created without content, use POST `/v1/documents/{document_id}/chunks` to fill
              it.

          is_separator_regex: Whether the separator is a regex to use for the upload file.

          metadata: Optional additional metadata to add to each chunk if a file is provided. Provide
              a stringified JSON object matching the Metadata schema.

          name: Name of document if no file is provided or to override file name.

          preset_separators: Preset separators used by RecursiveCharacterTextSplitter for further splitting.
              See
              [implemented details](https://github.com/langchain-ai/langchain/blob/eb122945832eae9b9df7c70ccd8d51fcd7a1899b/libs/text-splitters/langchain_text_splitters/character.py#L164).

          separators: Delimiters used by RecursiveCharacterTextSplitter for further splitting. If
              provided, `preset_separators` is ignored.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "chunk_min_size": chunk_min_size,
                "chunk_overlap": chunk_overlap,
                "chunk_size": chunk_size,
                "collection": collection,
                "collection_id": collection_id,
                "disable_chunking": disable_chunking,
                "file": file,
                "is_separator_regex": is_separator_regex,
                "metadata": metadata,
                "name": name,
                "preset_separators": preset_separators,
                "separators": separators,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(
            "/v1/documents",
            body=maybe_transform(body, document_create_params.DocumentCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=DocumentCreateResponse,
        )

    def retrieve(
        self,
        document_id: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> DocumentRetrieveResponse:
        """
        Get a document by ID.

        Args:
          document_id: The document ID

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            f"/v1/documents/{document_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=DocumentRetrieveResponse,
        )

    def list(
        self,
        *,
        collection_id: Optional[int] | Omit = omit,
        limit: int | Omit = omit,
        name: Optional[str] | Omit = omit,
        offset: int | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> object:
        """
        Get all documents ID from a collection.

        Args:
          collection_id: Filter documents by collection ID

          limit: The number of documents to return

          name: Filter documents by name

          offset: The offset of the first document to return

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            "/v1/documents",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "collection_id": collection_id,
                        "limit": limit,
                        "name": name,
                        "offset": offset,
                    },
                    document_list_params.DocumentListParams,
                ),
            ),
            cast_to=object,
        )

    def delete(
        self,
        document_id: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Delete a document.

        Args:
          document_id: The document ID

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._delete(
            f"/v1/documents/{document_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class AsyncDocumentsResource(AsyncAPIResource):
    @cached_property
    def chunks(self) -> AsyncChunksResource:
        return AsyncChunksResource(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncDocumentsResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return AsyncDocumentsResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncDocumentsResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return AsyncDocumentsResourceWithStreamingResponse(self)

    async def create(
        self,
        *,
        chunk_min_size: int | Omit = omit,
        chunk_overlap: int | Omit = omit,
        chunk_size: int | Omit = omit,
        collection: Optional[int] | Omit = omit,
        collection_id: Optional[int] | Omit = omit,
        disable_chunking: bool | Omit = omit,
        file: Optional[FileTypes] | Omit = omit,
        is_separator_regex: bool | Omit = omit,
        metadata: str | Omit = omit,
        name: Optional[str] | Omit = omit,
        preset_separators: Literal[
            "cpp",
            "go",
            "java",
            "kotlin",
            "js",
            "ts",
            "php",
            "proto",
            "python",
            "r",
            "rst",
            "ruby",
            "rust",
            "scala",
            "swift",
            "markdown",
            "latex",
            "html",
            "sol",
            "csharp",
            "cobol",
            "c",
            "lua",
            "perl",
            "haskell",
            "elixir",
            "powershell",
            "visualbasic6",
        ]
        | Omit = omit,
        separators: SequenceNotStr[str] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> DocumentCreateResponse:
        """Upload a file, parse and split it into chunks, then create a document.

        If no
        file is provided, the document will be created without content, use POST
        `/v1/documents/{document_id}/chunks` to fill it.

        Args:
          chunk_min_size: The minimum size in characters of the chunks to use for the upload file.

          chunk_overlap: The overlap in characters of the chunks to use for the upload file.

          chunk_size: The size in characters of the chunks to use for the upload file. If not
              provided, the document will not be split into chunks.

          collection_id: The collection ID to use for the file upload. The file will be vectorized with
              model defined by the collection.

          disable_chunking: Whether to disable `RecursiveCharacterTextSplitter` chunking for the upload
              file.

          file: The file to create a document from. If not provided, the document will be
              created without content, use POST `/v1/documents/{document_id}/chunks` to fill
              it.

          is_separator_regex: Whether the separator is a regex to use for the upload file.

          metadata: Optional additional metadata to add to each chunk if a file is provided. Provide
              a stringified JSON object matching the Metadata schema.

          name: Name of document if no file is provided or to override file name.

          preset_separators: Preset separators used by RecursiveCharacterTextSplitter for further splitting.
              See
              [implemented details](https://github.com/langchain-ai/langchain/blob/eb122945832eae9b9df7c70ccd8d51fcd7a1899b/libs/text-splitters/langchain_text_splitters/character.py#L164).

          separators: Delimiters used by RecursiveCharacterTextSplitter for further splitting. If
              provided, `preset_separators` is ignored.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "chunk_min_size": chunk_min_size,
                "chunk_overlap": chunk_overlap,
                "chunk_size": chunk_size,
                "collection": collection,
                "collection_id": collection_id,
                "disable_chunking": disable_chunking,
                "file": file,
                "is_separator_regex": is_separator_regex,
                "metadata": metadata,
                "name": name,
                "preset_separators": preset_separators,
                "separators": separators,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            "/v1/documents",
            body=await async_maybe_transform(body, document_create_params.DocumentCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=DocumentCreateResponse,
        )

    async def retrieve(
        self,
        document_id: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> DocumentRetrieveResponse:
        """
        Get a document by ID.

        Args:
          document_id: The document ID

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            f"/v1/documents/{document_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=DocumentRetrieveResponse,
        )

    async def list(
        self,
        *,
        collection_id: Optional[int] | Omit = omit,
        limit: int | Omit = omit,
        name: Optional[str] | Omit = omit,
        offset: int | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> object:
        """
        Get all documents ID from a collection.

        Args:
          collection_id: Filter documents by collection ID

          limit: The number of documents to return

          name: Filter documents by name

          offset: The offset of the first document to return

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            "/v1/documents",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=await async_maybe_transform(
                    {
                        "collection_id": collection_id,
                        "limit": limit,
                        "name": name,
                        "offset": offset,
                    },
                    document_list_params.DocumentListParams,
                ),
            ),
            cast_to=object,
        )

    async def delete(
        self,
        document_id: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Delete a document.

        Args:
          document_id: The document ID

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._delete(
            f"/v1/documents/{document_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class DocumentsResourceWithRawResponse:
    def __init__(self, documents: DocumentsResource) -> None:
        self._documents = documents

        self.create = to_raw_response_wrapper(
            documents.create,
        )
        self.retrieve = to_raw_response_wrapper(
            documents.retrieve,
        )
        self.list = to_raw_response_wrapper(
            documents.list,
        )
        self.delete = to_raw_response_wrapper(
            documents.delete,
        )

    @cached_property
    def chunks(self) -> ChunksResourceWithRawResponse:
        return ChunksResourceWithRawResponse(self._documents.chunks)


class AsyncDocumentsResourceWithRawResponse:
    def __init__(self, documents: AsyncDocumentsResource) -> None:
        self._documents = documents

        self.create = async_to_raw_response_wrapper(
            documents.create,
        )
        self.retrieve = async_to_raw_response_wrapper(
            documents.retrieve,
        )
        self.list = async_to_raw_response_wrapper(
            documents.list,
        )
        self.delete = async_to_raw_response_wrapper(
            documents.delete,
        )

    @cached_property
    def chunks(self) -> AsyncChunksResourceWithRawResponse:
        return AsyncChunksResourceWithRawResponse(self._documents.chunks)


class DocumentsResourceWithStreamingResponse:
    def __init__(self, documents: DocumentsResource) -> None:
        self._documents = documents

        self.create = to_streamed_response_wrapper(
            documents.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            documents.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            documents.list,
        )
        self.delete = to_streamed_response_wrapper(
            documents.delete,
        )

    @cached_property
    def chunks(self) -> ChunksResourceWithStreamingResponse:
        return ChunksResourceWithStreamingResponse(self._documents.chunks)


class AsyncDocumentsResourceWithStreamingResponse:
    def __init__(self, documents: AsyncDocumentsResource) -> None:
        self._documents = documents

        self.create = async_to_streamed_response_wrapper(
            documents.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            documents.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            documents.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            documents.delete,
        )

    @cached_property
    def chunks(self) -> AsyncChunksResourceWithStreamingResponse:
        return AsyncChunksResourceWithStreamingResponse(self._documents.chunks)
