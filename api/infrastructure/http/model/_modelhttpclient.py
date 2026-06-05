import ast
from http import HTTPMethod
from json import JSONDecodeError, dumps, loads
import logging
import time
import traceback
from typing import Annotated
from urllib.parse import urljoin
from uuid import uuid4

from fastapi import HTTPException
import httpx
from pydantic import BaseModel, Field, StringConstraints

from api.domain.model.entities import UserModelRequest
from api.domain.provider import ProviderMetricsLogger
from api.domain.provider.entities import Metric, ProviderType
from api.domain.provider.errors import UnsupportedEndpointError
from api.infrastructure.fastapi.context import RequestContextManager
from api.infrastructure.fastapi.endpoints.exceptions import ModelIsTooBusyException
from api.infrastructure.http.model.adapters import (
    AudioTranscriptionAdapter,
    ChatCompletionAdapter,
    EmbeddingsAdapter,
    EndpointAdapter,
    ModelsAdapter,
    OcrAdapter,
    RerankAdapter,
)
from api.infrastructure.http.model.exchanges import ModelHttpExchange, OriginalModelRequest, OriginalModelResponse
from api.schemas.chat import ChatCompletion, ChatCompletionChunk
from api.utils.variables import EndpointRoute

from ._modelusagecomputer import ModelUsageComputer

logger = logging.getLogger(__name__)


class ModelHttpClientEndpoints(BaseModel):
    audio_transcriptions: Annotated[tuple[HTTPMethod | None, Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True)]], Field(default=(HTTPMethod.POST, "/v1/audio/transcriptions"))]  # fmt: off
    chat_completions: Annotated[tuple[HTTPMethod | None, Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True)]], Field(default=(HTTPMethod.POST, "/v1/chat/completions"))]  # fmt: off
    embeddings: Annotated[tuple[HTTPMethod | None, Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True)]], Field(default=(HTTPMethod.POST, "/v1/embeddings"))]  # fmt: off
    models: Annotated[tuple[HTTPMethod | None, Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True)]], Field(default=(HTTPMethod.GET, "/v1/models"))]  # fmt: off
    ocr: Annotated[tuple[HTTPMethod | None, Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True)]], Field(default=(HTTPMethod.POST, "/v1/ocr"))]  # fmt: off
    rerank: Annotated[tuple[HTTPMethod | None, Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True)]], Field(default=(HTTPMethod.POST, "/v1/rerank"))]  # fmt: off

    def get_method_and_url(self, base_url: str, endpoint: EndpointRoute) -> tuple[HTTPMethod | None, str | None]:
        try:
            method, path = getattr(self, endpoint.name.lower())
        except AttributeError:
            return None, None
        base_url = base_url + "/" if not base_url.endswith("/") else base_url
        url = None if path is None else urljoin(base=base_url, url=path.lstrip("/"))
        return method, url


class ModelHttpClient:
    ENDPOINT_TABLE: ModelHttpClientEndpoints = ModelHttpClientEndpoints()
    TYPE: ProviderType

    def __init__(
        self,
        url: str,
        key: str,
        timeout: int,
        model_name: str,
        provider_metrics_logger: ProviderMetricsLogger,
        request_manager: RequestContextManager,
        usage_computer: ModelUsageComputer | None = None,
    ):
        """
        Initialize the model HTTP client. This class has four main methods:
        - build_request_exchange: Build an exchange from a request content.
        - forward_request: Forward a request to a provider model and add model name to the response. Optionally, add additional data to the response.
        - forward_stream: Forward a stream request to a provider model and add model name to the response. Optionally, add additional data to the response.
        - complete_response_exchange: Complete the response exchange by adding the model name, request ID and usage to the response.
        """
        self.provider_metrics_logger = provider_metrics_logger
        self.request_manager = request_manager
        self.usage_computer = usage_computer

        self.url = url
        self.key = key
        self.timeout = timeout
        self.model_name = model_name
        self.provider_id: int | None = None  # set by the ModelRegistry when the provider is created
        self.cost_prompt_tokens: float | None = None  # set by the ModelRegistry when the provider is retrieved
        self.cost_completion_tokens: float | None = None  # set by the ModelRegistry when the provider is retrieved

        self.headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}

        self.ENDPOINT_TABLE = self.ENDPOINT_TABLE.model_copy(deep=True)  # copy to avoid mutable conflict between classe instances
        self._adapters: dict[EndpointRoute, EndpointAdapter] = self._build_adapters()

    def _build_adapters(self) -> dict[EndpointRoute, EndpointAdapter]:
        return {
            EndpointRoute.AUDIO_TRANSCRIPTIONS: AudioTranscriptionAdapter(),
            EndpointRoute.CHAT_COMPLETIONS: ChatCompletionAdapter(),
            EndpointRoute.EMBEDDINGS: EmbeddingsAdapter(),
            EndpointRoute.MODELS: ModelsAdapter(),
            EndpointRoute.OCR: OcrAdapter(),
            EndpointRoute.RERANK: RerankAdapter(),
        }

    def build_request_exchange(self, user_request: UserModelRequest) -> ModelHttpExchange | UnsupportedEndpointError:
        exchange = ModelHttpExchange(original_request=OriginalModelRequest.from_user_request(user_request=user_request))

        method, url = self.ENDPOINT_TABLE.get_method_and_url(base_url=self.url, endpoint=exchange.original_request.endpoint)
        if method is None or url is None:
            return UnsupportedEndpointError(endpoint=exchange.original_request.endpoint, provider_type=self.TYPE)

        adapter = self._adapters.get(exchange.original_request.endpoint)
        if adapter:
            exchange.formatted_request = adapter.format_request(
                original_request=exchange.original_request, method=method, url=url, model_name=self.model_name
            )

        return exchange

    async def forward_request(self, exchange: ModelHttpExchange) -> httpx.Response:
        inflight_is_incremented = await self.provider_metrics_logger.increment_inflight(provider_id=self.provider_id)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as async_client:
                try:
                    start_time = time.perf_counter()
                    response = await async_client.request(
                        headers=self.headers,
                        method=exchange.formatted_request.method,
                        url=exchange.formatted_request.url,
                        json=exchange.formatted_request.body,
                        files=exchange.formatted_request.files,
                        data=exchange.formatted_request.form,
                    )
                except (
                    httpx.TimeoutException,
                    httpx.ReadTimeout,
                    httpx.ConnectTimeout,
                    httpx.WriteTimeout,
                    httpx.PoolTimeout,
                    httpx.RemoteProtocolError,
                    httpx.ConnectError,
                ) as e:
                    raise ModelIsTooBusyException(error_type=type(e).__name__)
                except Exception as e:
                    logger.exception(msg=f"Failed to forward request to {self.model_name}: {e}.")
                    raise HTTPException(status_code=500, detail=type(e).__name__)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError:
                    try:
                        message = loads(response.text)  # format error message
                        if "message" in message:
                            try:
                                message = ast.literal_eval(message["message"])
                            except Exception:
                                message = message["message"]
                    except JSONDecodeError:
                        logger.debug(traceback.format_exc())
                        message = response.text
                    raise HTTPException(status_code=response.status_code, detail=message)
        finally:
            await self.provider_metrics_logger.decrement_inflight(provider_id=self.provider_id, inflight_is_incremented=inflight_is_incremented)

        # add additional data to the response
        latency = self._elapsed_ms(start_time=start_time)
        response_data = response.json()
        exchange = self.complete_response_exchange(exchange=exchange, response_data=response_data, latency=latency)
        self.request_manager.set_ttft(None)
        self.request_manager.set_latency(latency)
        await self.provider_metrics_logger.log_metric(provider_id=self.provider_id, metric=Metric.LATENCY, value=latency)
        completion_tokens = exchange.formatted_response.data.usage.completion_tokens if exchange.formatted_response.data else 0
        await self.provider_metrics_logger.log_metric(
            provider_id=self.provider_id, metric=Metric.NORMALIZED_LATENCY, value=latency / max(1, completion_tokens)
        )

        if exchange.formatted_response.data is None:
            response = httpx.Response(
                status_code=response.status_code,
                content=exchange.formatted_response.text,
                headers={"Content-Type": "text/plain"},
            )
        else:
            response = httpx.Response(
                status_code=response.status_code,
                content=dumps(exchange.formatted_response.data.model_dump()),
                headers={"Content-Type": "application/json"},
            )

        return response

    async def forward_stream(self, exchange: ModelHttpExchange):
        """
        Forward a stream request to a provider model and add model name to the response. Optionally, add additional data to the response.

        Args:
            request_content(RequestContent): The request content to use for the request.
        """
        assert exchange.original_request.endpoint == EndpointRoute.CHAT_COMPLETIONS, "Only chat completions are supported for streaming"

        inflight_is_incremented = await self.provider_metrics_logger.increment_inflight(provider_id=self.provider_id)

        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                async with async_client.stream(
                    headers=self.headers,
                    method=exchange.formatted_request.method,
                    url=exchange.formatted_request.url,
                    json=exchange.formatted_request.body,
                    files=exchange.formatted_request.files,
                    data=exchange.formatted_request.form,
                ) as response:
                    buffer: list[dict] = []
                    start_time = time.perf_counter()
                    ttft: int | None = None
                    latency: int | None = None
                    include_usage: bool = False

                    async for chunk in response.aiter_lines():
                        # error case
                        if response.status_code // 100 != 2:
                            include_usage = True  # escape usage computation
                            yield chunk, response.status_code
                            break

                        # normal case
                        if chunk.strip() == "":
                            continue

                        parsed_chunk = ChatCompletionChunk.parse_chunk(chunk=chunk)

                        # exclude empty or malformed chunks to the buffer (for usage computation)
                        if parsed_chunk is not None and parsed_chunk != "[DONE]":
                            chunk_content = ChatCompletionChunk.extract_chunk_content(chunk=parsed_chunk)
                            buffer.append(chunk_content)

                            if "usage" in parsed_chunk:
                                include_usage = True
                                latency = self._elapsed_ms(start_time=start_time)
                                response_data = ChatCompletion(model=self.model_name, choices=[{"index": 0, "message": " ".join(buffer)}]).model_dump()  # fmt: off
                                exchange = self.complete_response_exchange(exchange=exchange, response_data=response_data, latency=latency)
                                parsed_chunk["usage"] = exchange.formatted_response.data.usage
                                chunk = f"data: {dumps(parsed_chunk)}"

                            if ttft is None and chunk_content:
                                ttft = self._elapsed_ms(start_time=start_time)

                        yield chunk + "\n\n", response.status_code

                if not include_usage:
                    latency = self._elapsed_ms(start_time=start_time)
                    response_data = ChatCompletion(model=self.model_name, choices=[{"index": 0, "message": " ".join(buffer)}]).model_dump()
                    exchange = self.complete_response_exchange(exchange=exchange, response_data=response_data, latency=latency)

                self.request_manager.set_ttft(ttft)
                self.request_manager.set_latency(latency)

                await self.provider_metrics_logger.log_metric(provider_id=self.provider_id, metric=Metric.TTFT, value=ttft)
                await self.provider_metrics_logger.log_metric(provider_id=self.provider_id, metric=Metric.LATENCY, value=latency)
                completion_tokens = exchange.formatted_response.data.usage.completion_tokens if exchange.formatted_response.data else 0
                await self.provider_metrics_logger.log_metric(
                    provider_id=self.provider_id, metric=Metric.NORMALIZED_LATENCY, value=latency / max(1, completion_tokens)
                )

            except (
                httpx.TimeoutException,
                httpx.ReadTimeout,
                httpx.ConnectTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
                httpx.RemoteProtocolError,
            ) as e:
                yield dumps({"detail": f"Model is too busy ({type(e).__name__}), please try again later."}), 503
            except httpx.ConnectError:
                yield dumps({"detail": "Model is temporarily unavailable, please try again later."}), 503
            except Exception as e:
                logger.exception(msg=f"Failed to forward stream request to {self.model_name}: {e}.")
                yield dumps({"detail": type(e).__name__}), 500
            finally:
                await self.provider_metrics_logger.decrement_inflight(provider_id=self.provider_id, inflight_is_incremented=inflight_is_incremented)

    def complete_response_exchange(self, exchange: ModelHttpExchange, response_data: dict, latency: int | None = None) -> ModelHttpExchange:
        exchange.original_response = OriginalModelResponse(data=response_data, latency=latency)

        adapter = self._adapters.get(exchange.original_request.endpoint)
        if adapter:
            request_id = self._get_request_id(exchange=exchange)
            self.request_manager.set_request_id(request_id)

            usage = self.request_manager.get_usage()
            if self.usage_computer is not None:
                usage = self.usage_computer.compute(
                    exchange=exchange,
                    usage=usage,
                    cost_prompt_tokens=self.cost_prompt_tokens,
                    cost_completion_tokens=self.cost_completion_tokens,
                )
                self.request_manager.set_usage(usage)

            exchange.formatted_response = adapter.format_response(exchange=exchange, request_id=request_id, usage=usage)

        return exchange

    def _get_request_id(self, exchange: ModelHttpExchange) -> str:
        request_id = self.request_manager.get_request_id()  # can be not None when the endpoint make multiple requests to a model (e.g. /v1/search)
        if "id" in exchange.original_response.data:
            request_id = exchange.original_response.data["id"]
        elif request_id is None:
            request_id = f"request-{str(uuid4()).replace('-', '')}"
        return request_id

    @staticmethod
    def _elapsed_ms(start_time: float) -> int:
        return int((time.perf_counter() - start_time) * 1000)  # ms
