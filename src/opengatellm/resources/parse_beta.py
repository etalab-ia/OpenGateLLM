# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import typing_extensions
from typing import Mapping, cast

import httpx

from ..types import parse_beta_parse_params
from .._types import Body, Omit, Query, Headers, NotGiven, FileTypes, omit, not_given
from .._utils import extract_files, maybe_transform, deepcopy_minimal, async_maybe_transform
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from .._base_client import make_request_options
from ..types.parse_beta_parse_response import ParseBetaParseResponse

__all__ = ["ParseBetaResource", "AsyncParseBetaResource"]


class ParseBetaResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> ParseBetaResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return ParseBetaResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ParseBetaResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return ParseBetaResourceWithStreamingResponse(self)

    @typing_extensions.deprecated("deprecated")
    def parse(
        self,
        *,
        file: FileTypes,
        force_ocr: bool | Omit = omit,
        page_range: str | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> ParseBetaParseResponse:
        """
        Parse a PDF file into markdown.

        Args:
          file: The file to parse.

          force_ocr: Force OCR on all pages of the PDF. Defaults to False. This can lead to worse
              results if you have good text in your PDFs (which is true in most cases).

          page_range:
              Page range to convert, specify comma separated page numbers or ranges. Example:
              '0,5-10,20'

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "file": file,
                "force_ocr": force_ocr,
                "page_range": page_range,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(
            "/v1/parse-beta",
            body=maybe_transform(body, parse_beta_parse_params.ParseBetaParseParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ParseBetaParseResponse,
        )


class AsyncParseBetaResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncParseBetaResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return AsyncParseBetaResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncParseBetaResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return AsyncParseBetaResourceWithStreamingResponse(self)

    @typing_extensions.deprecated("deprecated")
    async def parse(
        self,
        *,
        file: FileTypes,
        force_ocr: bool | Omit = omit,
        page_range: str | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> ParseBetaParseResponse:
        """
        Parse a PDF file into markdown.

        Args:
          file: The file to parse.

          force_ocr: Force OCR on all pages of the PDF. Defaults to False. This can lead to worse
              results if you have good text in your PDFs (which is true in most cases).

          page_range:
              Page range to convert, specify comma separated page numbers or ranges. Example:
              '0,5-10,20'

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "file": file,
                "force_ocr": force_ocr,
                "page_range": page_range,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            "/v1/parse-beta",
            body=await async_maybe_transform(body, parse_beta_parse_params.ParseBetaParseParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ParseBetaParseResponse,
        )


class ParseBetaResourceWithRawResponse:
    def __init__(self, parse_beta: ParseBetaResource) -> None:
        self._parse_beta = parse_beta

        self.parse = (  # pyright: ignore[reportDeprecated]
            to_raw_response_wrapper(
                parse_beta.parse,  # pyright: ignore[reportDeprecated],
            )
        )


class AsyncParseBetaResourceWithRawResponse:
    def __init__(self, parse_beta: AsyncParseBetaResource) -> None:
        self._parse_beta = parse_beta

        self.parse = (  # pyright: ignore[reportDeprecated]
            async_to_raw_response_wrapper(
                parse_beta.parse,  # pyright: ignore[reportDeprecated],
            )
        )


class ParseBetaResourceWithStreamingResponse:
    def __init__(self, parse_beta: ParseBetaResource) -> None:
        self._parse_beta = parse_beta

        self.parse = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                parse_beta.parse,  # pyright: ignore[reportDeprecated],
            )
        )


class AsyncParseBetaResourceWithStreamingResponse:
    def __init__(self, parse_beta: AsyncParseBetaResource) -> None:
        self._parse_beta = parse_beta

        self.parse = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                parse_beta.parse,  # pyright: ignore[reportDeprecated],
            )
        )
