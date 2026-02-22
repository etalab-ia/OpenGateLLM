# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Iterable, Optional

import httpx

from ..types import ocr_extract_text_params
from .._types import Body, Omit, Query, Headers, NotGiven, omit, not_given
from .._utils import maybe_transform, async_maybe_transform
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from .._base_client import make_request_options
from ..types.response_format_param import ResponseFormatParam
from ..types.ocr_extract_text_response import OcrExtractTextResponse

__all__ = ["OcrResource", "AsyncOcrResource"]


class OcrResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> OcrResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return OcrResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> OcrResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return OcrResourceWithStreamingResponse(self)

    def extract_text(
        self,
        *,
        document: ocr_extract_text_params.Document,
        bbox_annotation_format: Optional[ResponseFormatParam] | Omit = omit,
        document_annotation_format: Optional[ResponseFormatParam] | Omit = omit,
        image_limit: Optional[int] | Omit = omit,
        image_min_size: Optional[int] | Omit = omit,
        include_image_base64: Optional[bool] | Omit = omit,
        model: Optional[str] | Omit = omit,
        pages: Optional[Iterable[int]] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> OcrExtractTextResponse:
        """
        Extracts text from files using OCR.

        Args:
          document: Document to run OCR on.

          bbox_annotation_format: Specify the format that the model must output for the bounding boxes. By default
              it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables
              JSON mode, which guarantees the message the model generates is in JSON. When
              using JSON mode you MUST also instruct the model to produce JSON yourself with a
              system or a user message. Setting to `{ "type": "json_schema" }` enables JSON
              schema mode, which guarantees the message the model generates is in JSON and
              follows the schema you provide.

          document_annotation_format: Specify the format that the model must output for the document. By default it
              will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables
              JSON mode, which guarantees the message the model generates is in JSON. When
              using JSON mode you MUST also instruct the model to produce JSON yourself with a
              system or a user message. Setting to `{ "type": "json_schema" }` enables JSON
              schema mode, which guarantees the message the model generates is in JSON and
              follows the schema you provide.

          image_limit: Max images to extract

          image_min_size: Minimum height and width of image to extract

          include_image_base64: Include image URLs in response

          model: The model to use for the OCR.

          pages: Specific pages user wants to process in various formats: single number, range,
              or list of both. Starts from 0

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/v1/ocr",
            body=maybe_transform(
                {
                    "document": document,
                    "bbox_annotation_format": bbox_annotation_format,
                    "document_annotation_format": document_annotation_format,
                    "image_limit": image_limit,
                    "image_min_size": image_min_size,
                    "include_image_base64": include_image_base64,
                    "model": model,
                    "pages": pages,
                },
                ocr_extract_text_params.OcrExtractTextParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=OcrExtractTextResponse,
        )


class AsyncOcrResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncOcrResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return AsyncOcrResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncOcrResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return AsyncOcrResourceWithStreamingResponse(self)

    async def extract_text(
        self,
        *,
        document: ocr_extract_text_params.Document,
        bbox_annotation_format: Optional[ResponseFormatParam] | Omit = omit,
        document_annotation_format: Optional[ResponseFormatParam] | Omit = omit,
        image_limit: Optional[int] | Omit = omit,
        image_min_size: Optional[int] | Omit = omit,
        include_image_base64: Optional[bool] | Omit = omit,
        model: Optional[str] | Omit = omit,
        pages: Optional[Iterable[int]] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> OcrExtractTextResponse:
        """
        Extracts text from files using OCR.

        Args:
          document: Document to run OCR on.

          bbox_annotation_format: Specify the format that the model must output for the bounding boxes. By default
              it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables
              JSON mode, which guarantees the message the model generates is in JSON. When
              using JSON mode you MUST also instruct the model to produce JSON yourself with a
              system or a user message. Setting to `{ "type": "json_schema" }` enables JSON
              schema mode, which guarantees the message the model generates is in JSON and
              follows the schema you provide.

          document_annotation_format: Specify the format that the model must output for the document. By default it
              will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables
              JSON mode, which guarantees the message the model generates is in JSON. When
              using JSON mode you MUST also instruct the model to produce JSON yourself with a
              system or a user message. Setting to `{ "type": "json_schema" }` enables JSON
              schema mode, which guarantees the message the model generates is in JSON and
              follows the schema you provide.

          image_limit: Max images to extract

          image_min_size: Minimum height and width of image to extract

          include_image_base64: Include image URLs in response

          model: The model to use for the OCR.

          pages: Specific pages user wants to process in various formats: single number, range,
              or list of both. Starts from 0

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/v1/ocr",
            body=await async_maybe_transform(
                {
                    "document": document,
                    "bbox_annotation_format": bbox_annotation_format,
                    "document_annotation_format": document_annotation_format,
                    "image_limit": image_limit,
                    "image_min_size": image_min_size,
                    "include_image_base64": include_image_base64,
                    "model": model,
                    "pages": pages,
                },
                ocr_extract_text_params.OcrExtractTextParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=OcrExtractTextResponse,
        )


class OcrResourceWithRawResponse:
    def __init__(self, ocr: OcrResource) -> None:
        self._ocr = ocr

        self.extract_text = to_raw_response_wrapper(
            ocr.extract_text,
        )


class AsyncOcrResourceWithRawResponse:
    def __init__(self, ocr: AsyncOcrResource) -> None:
        self._ocr = ocr

        self.extract_text = async_to_raw_response_wrapper(
            ocr.extract_text,
        )


class OcrResourceWithStreamingResponse:
    def __init__(self, ocr: OcrResource) -> None:
        self._ocr = ocr

        self.extract_text = to_streamed_response_wrapper(
            ocr.extract_text,
        )


class AsyncOcrResourceWithStreamingResponse:
    def __init__(self, ocr: AsyncOcrResource) -> None:
        self._ocr = ocr

        self.extract_text = async_to_streamed_response_wrapper(
            ocr.extract_text,
        )
