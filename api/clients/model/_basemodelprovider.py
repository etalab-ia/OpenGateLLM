from abc import ABC
import ast
import importlib
from json import JSONDecodeError, dumps, loads
import logging
import time
import traceback
from urllib.parse import urljoin

from fastapi import HTTPException
import httpx
from redis.asyncio import Redis as AsyncRedis

from api.schemas.admin.providers import ProviderType
from api.schemas.audio import AudioTranscription, CreateAudioTranscription
from api.schemas.chat import ChatCompletionChunk, CreateChatCompletion
from api.schemas.core.models import Metric, ProviderEndpoints, RequestContent
from api.schemas.rerank import CreateRerank, Reranks
from api.schemas.usage import Usage
from api.utils.carbon import get_carbon_footprint
from api.utils.context import generate_request_id, global_context, request_context
from api.utils.exceptions import ModelIsTooBusyException, RequestFormatFailedException, ResponseFormatFailedException
from api.utils.redis import redis_retry, safe_redis_reset
from api.utils.variables import (
    PREFIX__REDIS_METRIC_GAUGE,
    PREFIX__REDIS_METRIC_TIMESERIE,
    REDIS__TIMESERIE_RETENTION_SECONDS,
    EndpointRoute,
)

logger = logging.getLogger(__name__)


class BaseModelProvider(ABC):
    ENDPOINT_TABLE: ProviderEndpoints = ProviderEndpoints()

    def __init__(
        self,
        url: str,
        key: str,
        timeout: int,
        model_name: str,
        model_hosting_zone: str | None,
        model_total_params: int | None,
        model_active_params: int | None,
    ) -> None:
        self.model_name = model_name
        self.model_hosting_zone = model_hosting_zone
        self.model_total_params = model_total_params
        self.model_active_params = model_active_params
        self.url = url
        self.key = key
        self.timeout = timeout

        self.type: ProviderType | None = None  # set by the child ModelProvider class when the provider is created
        self.id: int | None = None  # set by the ModelRegistry when the provider is created
        self.cost_prompt_tokens: float | None = None  # set by the ModelRegistry when the provider is retrieved
        self.cost_completion_tokens: float | None = None  # set by the ModelRegistry when the provider is retrieved

        self.headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}

    @staticmethod
    def import_module(type: ProviderType) -> "type[BaseModelProvider]":
        """
        Static method to import a subclass of BaseModelProvider.

        Args:
            type(str): The type of model provider to import.

        Returns:
            Type[BaseModelProvider]: The subclass of BaseModelProvider.
        """

        module = importlib.import_module(f"api.clients.model._{type.value}modelprovider")

        return getattr(module, f"{type.capitalize()}ModelProvider")

    @staticmethod
    async def get_max_context_length() -> int | None:
        """
        Get the max context length of the model provider to store in the database. Useful
        to check provider consistency.
        """
        pass

    async def get_vector_size(self) -> int | None:
        if self.ENDPOINT_TABLE.embeddings is None:
            return None

        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE.embeddings.lstrip("/"))

        async with httpx.AsyncClient() as client:
            response = await client.post(url=url, headers=self.headers, json={"model": self.model_name, "input": "hello world"}, timeout=self.timeout)
            assert response.status_code == 200, f"Model is not reachable ({response.status_code} - {response.text})."

        data = response.json()["data"]
        vector_size = len(data[0]["embedding"])

        return vector_size

    def _get_usage(self, request_content: RequestContent, response_data: dict | list[dict], request_latency: float | None = 0.0) -> Usage | None:
        """
        Get usage data from request and response.

        Args:
            request_content(RequestContent): The request content.
            response_data(dict | list[dict]): The data of the response.
            request_latency(float): The request latency in seconds.

        Returns:
            Usage | None: The usage data.
        """

        usage = request_context.get().usage
        # In Celery worker processes the FastAPI app initialization (which sets global_context.tokenizer)
        # might not have fully run. Accessing global_context.tokenizer directly could raise AttributeError.
        # We skip usage computation if tokenizer is absent so we still return the provider response.
        tokenizer = getattr(global_context, "tokenizer", None)
        if tokenizer and request_content.endpoint in tokenizer.USAGE_ENDPOINTS:
            try:
                completion_tokens = 0
                prompt_tokens = tokenizer.get_prompt_tokens(endpoint=request_content.endpoint, body=request_content.json)
                completion_tokens = tokenizer.get_completion_tokens(endpoint=request_content.endpoint, response_data=response_data)
                total_tokens = prompt_tokens + completion_tokens

                carbon_footprint = get_carbon_footprint(
                    active_params=self.model_active_params,
                    total_params=self.model_total_params,
                    model_zone=self.model_hosting_zone,
                    token_count=total_tokens,
                    request_latency=request_latency,
                )
                cost = round(prompt_tokens / 1000000 * self.cost_prompt_tokens + completion_tokens / 1000000 * self.cost_completion_tokens, ndigits=6)  # fmt: off

                usage.prompt_tokens += prompt_tokens
                usage.completion_tokens += completion_tokens
                usage.total_tokens += total_tokens
                usage.cost += cost
                usage.carbon.kgCO2eq.min += carbon_footprint.kgCO2eq.min
                usage.carbon.kgCO2eq.max += carbon_footprint.kgCO2eq.max
                usage.carbon.kWh.min += carbon_footprint.kWh.min
                usage.carbon.kWh.max += carbon_footprint.kWh.max
                usage.requests += 1

                request_context.get().usage = usage

            except Exception as e:
                logger.exception(msg=f"Failed to compute usage values for endpoint {request_content.endpoint}: {e}.")

        return usage

    def _format_request(self, request_content: RequestContent) -> RequestContent:
        """
        Format a request to a provider model. This method can be overridden by a subclass to add additional headers or parameters. This method format the requested endpoint thanks the ENDPOINT_TABLE attribute.

        Args:
            content(RequestContent): The request content to format.

        Returns:
            content(RequestContent): The formatted request content.
        """
        if "model" in request_content.json:
            request_content.json["model"] = self.model_name

        if "model" in request_content.form:
            request_content.form["model"] = self.model_name
        try:
            if request_content.endpoint == EndpointRoute.AUDIO_TRANSCRIPTIONS:
                request_content = CreateAudioTranscription.format_request(provider_type=self.type, request_content=request_content)

            if request_content.endpoint == EndpointRoute.CHAT_COMPLETIONS:
                request_content = CreateChatCompletion.format_request(provider_type=self.type, request_content=request_content)

            if request_content.endpoint == EndpointRoute.RERANK:
                request_content = CreateRerank.format_request(provider_type=self.type, request_content=request_content)

        except Exception as e:
            logger.error(f"Failed to format request for {self.model_name}: {e}.", exc_info=True)
            raise RequestFormatFailedException()

        return request_content

    def _format_response(self, request_content: RequestContent, response: httpx.Response, request_latency: int | None = None) -> httpx.Response:
        """
        Format a response from a TEI model, overridden base class method to convert TEI reranking response to a standard response.
        """

        content_type = response.headers.get("Content-Type", "")
        if content_type == "application/json":
            response_data = response.json()

            usage = self._get_usage(request_content=request_content, response_data=response_data, request_latency=request_latency)

            if request_context.get().id is None:
                if isinstance(response_data, dict) and "id" in response_data:
                    request_context.get().id = response_data["id"]
                else:
                    request_context.get().id = generate_request_id()

            additional_data = request_content.additional_data
            additional_data.update({"model": request_content.model, "id": request_context.get().id, "usage": usage.model_dump()})

            try:
                if request_content.endpoint == EndpointRoute.AUDIO_TRANSCRIPTIONS:
                    response_data = AudioTranscription.build_from(
                        provider_type=self.type,
                        request_content=request_content,
                        response_data=response_data,
                    ).model_dump()

                elif request_content.endpoint == EndpointRoute.RERANK:
                    response_data = Reranks.build_from(
                        provider_type=self.type,
                        request_content=request_content,
                        response_data=response_data,
                    ).model_dump()

                else:
                    response_data.update(additional_data)

            except Exception as e:
                logger.error(f"Failed to build response from {self.model_name}: {e}.", exc_info=True)
                raise ResponseFormatFailedException()

            response = httpx.Response(status_code=response.status_code, content=dumps(response_data))

        return response

    async def _ensure_timeseries_exists(self, redis_client: AsyncRedis, key: str) -> None:
        """
        Ensure a time series exists with proper retention configuration.

        Args:
            redis_client(AsyncRedis): The redis client to use.
            key(str): The time series key to create.
        """
        try:
            await redis_client.ts().info(key)
        except Exception:
            try:
                await redis_client.ts().create(key, retention_msecs=REDIS__TIMESERIE_RETENTION_SECONDS * 1000, duplicate_policy="LAST")
            except Exception:
                pass

    async def _log_performance_metric(self, redis_client: AsyncRedis, ttft: int | None, latency: int | None) -> None:
        """
        Log performance metrics in redis.

        Args:
            redis_client(AsyncRedis): The redis client to use for the request.
            ttft(int | None): The time to first token in milliseconds (ms).
            latency(int | None): The latency in milliseconds (ms).
        """
        request_context.get().ttft = ttft
        request_context.get().latency = latency

        try:
            if ttft is not None:
                key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.TTFT.value}:{self.id}"
                await self._ensure_timeseries_exists(redis_client, key)
                await redis_client.ts().add(key=key, timestamp=int(time.time() * 1000), value=ttft)
        except Exception:
            logger.error(f"Failed to log request metrics (TTFT) in redis (id: {self.id})", exc_info=True)
            await safe_redis_reset(redis_client)

        try:
            if latency is not None:
                key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.LATENCY.value}:{self.id}"
                await self._ensure_timeseries_exists(redis_client, key)
                # Use milliseconds timestamp to avoid collisions
                await redis_client.ts().add(key=key, timestamp=int(time.time() * 1000), value=latency)
        except Exception:
            logger.error(f"Failed to log request metrics (latency) in redis (id: {self.id})", exc_info=True)
            await safe_redis_reset(redis_client)

    @staticmethod
    def _elapsed_ms(start_time: float) -> int:
        return int((time.perf_counter() - start_time) * 1000)  # ms

    async def forward_request(self, request_content: RequestContent, redis_client: AsyncRedis) -> httpx.Response:
        """
        Forward a request to a provider model and add model name to the response. Optionally, add additional data to the response.

        Args:
            redis_client(AsyncRedis): The redis client to use for the request.
            request_content(RequestContent): The request content to use for the request.

        Returns:
            httpx.Response: The response from the API.
        """

        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE.get_endpoint(endpoint=request_content.endpoint).lstrip("/"))
        request_content = self._format_request(request_content=request_content)

        inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{self.id}"
        try:
            await redis_retry(redis_client.incr, name=inflight_key, max_retries=2)

            async with httpx.AsyncClient(timeout=self.timeout) as async_client:
                try:
                    start_time = time.perf_counter()
                    response = await async_client.request(
                        method=request_content.method,
                        url=url,
                        headers=self.headers,
                        json=request_content.json,
                        files=request_content.files,
                        data=request_content.form,
                    )
                except (
                    httpx.TimeoutException,
                    httpx.ReadTimeout,
                    httpx.ConnectTimeout,
                    httpx.WriteTimeout,
                    httpx.PoolTimeout,
                    httpx.RemoteProtocolError,
                ) as e:
                    raise ModelIsTooBusyException(detail=f"Model is too busy ({type(e).__name__}), please try again later")
                except httpx.ConnectError:
                    raise ModelIsTooBusyException(detail="Model is temporarily unavailable, please try again later.")
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
            await redis_retry(redis_client.decr, name=inflight_key, max_retries=2)

        # add additional data to the response
        latency = self._elapsed_ms(start_time=start_time)
        response = self._format_response(request_content=request_content, response=response, request_latency=latency)
        await self._log_performance_metric(redis_client=redis_client, ttft=None, latency=latency)

        return response

    def _get_extra_stream_chunk(self, request_content: RequestContent, buffer: list[dict], latency: float | None = None) -> dict | None:
        """
        Get the extra chunk for a streaming response with usage and additional data.

        Args:
            request_content (RequestContent): The request content.
            buffer (list[dict]): List of response parsed chunks.
            latency (float | None): The latency in milliseconds.

        Returns:
            dict | None: The extra chunk.
        """
        if request_content.endpoint != EndpointRoute.CHAT_COMPLETIONS:
            return

        if len(buffer) == 0:
            return

        usage = self._get_usage(request_content=request_content, response_data=buffer, request_latency=latency)
        if request_context.get().id is None:
            request_id = buffer[0].get("id", generate_request_id())
            request_context.get().id = request_id
        else:
            request_id = request_context.get().id

        additional_data = request_content.additional_data
        additional_data.update({"model": self.model_name, "id": request_id, "usage": usage.model_dump()})
        extra_chunk = buffer[-1].copy()
        extra_chunk["choices"] = []
        extra_chunk.update(additional_data)

        return extra_chunk

    async def forward_stream(self, request_content: RequestContent, redis_client: AsyncRedis):
        """
        Forward a stream request to a provider model and add model name to the response. Optionally, add additional data to the response.

        Args:
            redis_client(AsyncRedis): The redis client to use for the request.
            request_content(RequestContent): The request content to use for the request.
        """
        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE.get_endpoint(endpoint=request_content.endpoint).lstrip("/"))
        request_content = self._format_request(request_content=request_content)

        inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{self.id}"
        inflight_incremented = False

        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                await redis_retry(redis_client.incr, name=inflight_key, max_retries=2)
                inflight_incremented = True
            except Exception:
                logger.error("Unable to increment redis requests inflight key")

            try:
                async with async_client.stream(
                    method=request_content.method,
                    url=url,
                    headers=self.headers,
                    json=request_content.json,
                    files=request_content.files,
                    data=request_content.form,
                ) as response:
                    buffer: list[dict] = []
                    start_time = time.perf_counter()
                    ttft: int | None = None
                    latency: int | None = None
                    done_chunk: bool = False

                    async for chunk in response.aiter_lines():
                        # error case
                        if response.status_code // 100 != 2:
                            done_chunk = True
                            yield chunk, response.status_code
                            break

                        # normal case
                        if chunk.strip() == "":
                            continue

                        parsed_chunk = ChatCompletionChunk.parse_chunk(chunk=chunk)
                        if parsed_chunk != "[DONE]":
                            if parsed_chunk is not None:  # exclude empty or malformed chunks to the buffer (for usage computation)
                                buffer.append(parsed_chunk)
                                if ttft is None and ChatCompletionChunk.extract_chunk_content(chunk=parsed_chunk):
                                    ttft = self._elapsed_ms(start_time=start_time)

                            yield chunk + "\n\n", response.status_code

                        # end of the stream
                        else:
                            done_chunk = True
                            latency = self._elapsed_ms(start_time=start_time)
                            extra_chunk = self._get_extra_stream_chunk(request_content=request_content, buffer=buffer, latency=latency)
                            if extra_chunk is not None:
                                yield f"data: {dumps(extra_chunk)}\n\n", response.status_code

                            yield chunk + "\n\n", response.status_code

                # edge case: stream ended without a [DONE] chunk
                if not done_chunk:
                    latency = self._elapsed_ms(start_time=start_time)
                    extra_chunk = self._get_extra_stream_chunk(request_content=request_content, buffer=buffer, latency=latency)
                    if extra_chunk is not None:
                        yield f"data: {dumps(extra_chunk)}\n\n", response.status_code

                await self._log_performance_metric(redis_client=redis_client, ttft=ttft, latency=latency)

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
                if inflight_incremented:
                    try:
                        await redis_retry(redis_client.decr, name=inflight_key, max_retries=2)
                    except Exception:
                        logger.error("Unable to decrement redis requests inflight key")
