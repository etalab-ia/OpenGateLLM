from abc import ABC
import ast
import importlib
from json import JSONDecodeError, dumps, loads
import logging
import re
import time
import traceback
from typing import Any
from urllib.parse import urljoin

from fastapi import HTTPException
import httpx
from redis.asyncio import Redis as AsyncRedis

from api.schemas.admin.providers import ProviderType
from api.schemas.core.metrics import Metric
from api.schemas.usage import Detail, Usage
from api.utils.carbon import get_carbon_footprint
from api.utils.context import generate_request_id, global_context, request_context
from api.utils.exceptions import ModelIsTooBusyException
from api.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__MODELS,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
    PREFIX__REDIS_METRIC_GAUGE,
    PREFIX__REDIS_METRIC_TIMESERIE,
    REDIS__TIMESERIE_RETENTION_SECONDS,
)

logger = logging.getLogger(__name__)


class BaseModelProvider(ABC):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: None,
        ENDPOINT__CHAT_COMPLETIONS: None,
        ENDPOINT__EMBEDDINGS: None,
        ENDPOINT__MODELS: None,
        ENDPOINT__OCR: None,
        ENDPOINT__RERANK: None,
    }

    def __init__(
        self,
        url: str,
        key: str,
        timeout: int,
        model_name: str,
        model_carbon_footprint_zone: str | None,
        model_carbon_footprint_total_params: int | None,
        model_carbon_footprint_active_params: int | None,
    ) -> None:
        self.name = model_name

        self.carbon_footprint_zone = model_carbon_footprint_zone
        self.carbon_footprint_total_params = model_carbon_footprint_total_params
        self.carbon_footprint_active_params = model_carbon_footprint_active_params
        self.url = url
        self.key = key
        self.timeout = timeout

        self.id = None  # set by the ModelRegistry when the provider is created
        self.cost_prompt_tokens = None  # set by the ModelRegistry when the provider is retrieved
        self.cost_completion_tokens = None  # set by the ModelRegistry when the provider is retrieved

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
    async def get_max_context_length(self) -> int | None:
        """
        Get the max context length of the model provider to store in the database. Useful
        to check provider consistency.
        """
        pass

    async def get_vector_size(self) -> int | None:
        if self.ENDPOINT_TABLE[ENDPOINT__EMBEDDINGS] is None:
            return None

        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE[ENDPOINT__EMBEDDINGS].lstrip("/"))

        async with httpx.AsyncClient() as client:
            response = await client.post(url=url, headers=self.headers, json={"model": self.name, "input": "hello world"}, timeout=self.timeout)
            assert response.status_code == 200, f"Model is not reachable ({response.status_code} - {response.text})."

        data = response.json()["data"]
        vector_size = len(data[0]["embedding"])

        return vector_size

    def _get_usage(self, json: dict, data: dict | list[dict], stream: bool, endpoint: str, request_latency: float = 0.0) -> Usage | None:
        """
        Get usage data from request and response.

        Args:
            json(dict): The JSON body of the request.
            data(dict): The data of the response.
            stream(bool): Whether the response is a stream.

        Returns:
            Dict[str, Any]: The additional data with usage data.
        """

        usage = None

        # In Celery worker processes the FastAPI app initialization (which sets global_context.tokenizer)
        # might not have fully run. Accessing global_context.tokenizer directly could raise AttributeError.
        # We skip usage computation if tokenizer is absent so we still return the provider response.
        tokenizer = getattr(global_context, "tokenizer", None)
        if tokenizer and endpoint in tokenizer.USAGE_COMPLETION_ENDPOINTS:
            try:
                usage = request_context.get().usage

                # compute usage for the current (add a detail object)
                detail_id = data[0].get("id", generate_request_id()) if stream else data.get("id", generate_request_id())
                detail = Detail(id=detail_id, model=self.name, usage=Usage())
                detail.usage.prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=endpoint, body=json)

                if tokenizer.USAGE_COMPLETION_ENDPOINTS[endpoint]:
                    detail.usage.completion_tokens = tokenizer.get_completion_tokens(
                        endpoint=endpoint,
                        response=data,
                        stream=stream,
                    )

                # @TODO: don't compute carbon if model type is not text-generation or image-text-to-text
                detail.usage.total_tokens = detail.usage.prompt_tokens + detail.usage.completion_tokens
                detail.usage.carbon = get_carbon_footprint(
                    active_params=self.carbon_footprint_active_params,
                    total_params=self.carbon_footprint_total_params,
                    model_zone=self.carbon_footprint_zone,
                    token_count=detail.usage.total_tokens,
                    request_latency=request_latency,
                )
                detail.usage.cost = round(detail.usage.prompt_tokens / 1000000 * self.cost_prompt_tokens + detail.usage.completion_tokens / 1000000 * self.cost_completion_tokens, ndigits=6)  # fmt: off
                usage.details.append(detail)

                # add token usage to the total usage
                usage.prompt_tokens += detail.usage.prompt_tokens
                usage.completion_tokens += detail.usage.completion_tokens
                usage.total_tokens += detail.usage.total_tokens

                # add cost to the total usage
                usage.cost += detail.usage.cost

                # add carbon usage to the total usage
                if detail.usage.carbon.kgCO2eq.min is not None:
                    if usage.carbon.kgCO2eq.min is None:
                        usage.carbon.kgCO2eq.min = 0.0
                    usage.carbon.kgCO2eq.min += detail.usage.carbon.kgCO2eq.min
                if detail.usage.carbon.kgCO2eq.max is not None:
                    if usage.carbon.kgCO2eq.max is None:
                        usage.carbon.kgCO2eq.max = 0.0
                    usage.carbon.kgCO2eq.max += detail.usage.carbon.kgCO2eq.max
                if detail.usage.carbon.kWh.min is not None:
                    if usage.carbon.kWh.min is None:
                        usage.carbon.kWh.min = 0.0
                    usage.carbon.kWh.min += detail.usage.carbon.kWh.min
                if detail.usage.carbon.kWh.max is not None:
                    if usage.carbon.kWh.max is None:
                        usage.carbon.kWh.max = 0.0
                    usage.carbon.kWh.max += detail.usage.carbon.kWh.max

            except Exception as e:
                logger.exception(msg=f"Failed to compute usage values for endpoint {endpoint}: {e}.")

        return usage

    def _get_additional_data(self, json: dict, data: dict | list[dict], stream: bool, endpoint: str, request_latency: float = 0.0) -> dict:
        """
        Get additional data from request and response.
        """
        usage = self._get_usage(json=json, data=data, stream=stream, endpoint=endpoint, request_latency=request_latency)
        request_id = usage.details[-1].id if usage and usage.details else generate_request_id()
        additional_data = {"model": self.name, "id": request_id}

        if usage:
            additional_data["usage"] = usage.model_dump()

        return additional_data

    def _format_request(
        self,
        json: dict | None = None,
        files: dict | None = None,
        data: dict | None = None,
        endpoint: str | None = None,
    ) -> tuple[str, dict[str, str] | None, dict | None, dict | None, dict | None]:
        """
        Format a request to a provider model. This method can be overridden by a subclass to add additional headers or parameters. This method format the requested endpoint thanks the ENDPOINT_TABLE attribute.

        Args:
            json(dict): The JSON body to use for the request.
            files(dict): The files to use for the request.
            data(dict): The data to use for the request.
            endpoint(str): The endpoint to use for the request.

        Returns:
            tuple: The formatted request composed of the url, headers, json, files and data.
        """
        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE[endpoint].lstrip("/"))
        if json and "model" in json:
            json["model"] = self.name

        return url, json, files, data

    def _format_response(
        self,
        json: dict,
        response: httpx.Response,
        endpoint: str,
        additional_data: dict[str, Any] | None = None,
        request_latency: float = 0.0,
    ) -> httpx.Response:
        """
        Format a response from a provider model and add usage data and model ID to the response. This method can be overridden by a subclass to add additional headers or parameters.

        Args:
            json(dict): The JSON body of the request to the API.
            response(httpx.Response): The response from the API.
            endpoint(str): The endpoint to use for the request.
            additional_data(Dict[str, Any]): The additional data to add to the response (default: {}).
            request_latency(float): The request latency in seconds.

        Returns:
            httpx.Response: The formatted response.
        """

        if additional_data is None:
            additional_data = {}

        content_type = response.headers.get("Content-Type", "")
        if content_type == "application/json":
            data = response.json()
            data.update(self._get_additional_data(json=json, data=data, stream=False, endpoint=endpoint, request_latency=request_latency))
            data.update(additional_data)
            response = httpx.Response(status_code=response.status_code, content=dumps(data))

        return response

    async def _ensure_timeseries_exists(self, redis_client: AsyncRedis, key: str) -> None:
        """
        Ensure a time series exists with proper retention configuration.

        Args:
            redis_client(AsyncRedis): The redis client to use.
            key(str): The time series key to create.
        """
        try:
            # Check if the time series already exists
            await redis_client.ts().info(key)
        except Exception:
            # Time series doesn't exist, create it with retention
            try:
                await redis_client.ts().create(key, retention_msecs=REDIS__TIMESERIE_RETENTION_SECONDS * 1000, duplicate_policy="LAST")
            except Exception:
                # Time series might have been created by another concurrent request, ignore
                pass

    async def _log_performance_metric(self, redis_client: AsyncRedis, ttft: int | None, latency: int | None) -> None:
        """
        Log performance metrics in redis.

        Args:
            redis_client(AsyncRedis): The redis client to use for the request.
            ttft(int | None): The time to first token in microseconds (us).
            latency(int | None): The latency in milliseconds (ms).
        """
        try:
            if ttft is not None:
                key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.TTFT.value}:{self.id}"
                await self._ensure_timeseries_exists(redis_client, key)
                await redis_client.ts().add(key, "*", ttft)
        except Exception:
            logger.error(f"Failed to log request metrics (TTFT) in redis (id: {self.id})", exc_info=True)
            await redis_client.reset()

        try:
            if latency is not None:
                key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.LATENCY.value}:{self.id}"
                await self._ensure_timeseries_exists(redis_client, key)
                await redis_client.ts().add(key, "*", latency)
        except Exception:
            logger.error(f"Failed to log request metrics (latency) in redis (id: {self.id})", exc_info=True)
            await redis_client.reset()

    async def forward_request(
        self,
        method: str,
        endpoint: str,
        redis_client: AsyncRedis,
        json: dict | None = None,
        files: dict | None = None,
        data: dict | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """
        Forward a request to a provider model and add model name to the response. Optionally, add additional data to the response.

        Args:
            method(str): The method to use for the request.
            endpoint(str): The endpoint to use for the request.
            redis_client(AsyncRedis): The redis client to use for the request.
            json(Optional[dict]): The JSON body to use for the request.
            files(Optional[dict]): The files to use for the request.
            data(Optional[dict]): The data to use for the request.
            additional_data(Dict[str, Any]): The additional data to add to the response (default: {}).

        Returns:
            httpx.Response: The response from the API.
        """

        url, json, files, data = self._format_request(json=json, files=files, data=data, endpoint=endpoint)
        if not additional_data:
            additional_data = {}

        inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{self.id}"
        try:
            try:
                await redis_client.incr(inflight_key)
            except Exception:
                logger.error("Unable to increment redis inflight key")

            async with httpx.AsyncClient(timeout=self.timeout) as async_client:
                try:
                    start_time = time.perf_counter()
                    response = await async_client.request(method=method, url=url, headers=self.headers, json=json, files=files, data=data)
                    end_time = time.perf_counter()
                except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout):
                    raise ModelIsTooBusyException()
                except Exception as e:
                    logger.exception(msg=f"Failed to forward request to {self.name}: {e}.")
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
            try:
                await redis_client.decr(inflight_key)
            except Exception:
                logger.error("Unable to decrement redis requests inflight key")

        # add additional data to the response
        request_latency = end_time - start_time
        response = self._format_response(
            json=json,
            response=response,
            additional_data=additional_data,
            endpoint=endpoint,
            request_latency=request_latency,
        )
        await self._log_performance_metric(redis_client=redis_client, ttft=None, latency=int(request_latency * 1_000))

        return response

    def _format_stream_response(
        self,
        json: dict,
        response: list,
        endpoint: str,
        additional_data: dict[str, Any] | None = None,
        request_latency: float = 0.0,
    ) -> tuple | None:
        """
        Format streaming response data for chat completions.

        Args:
            json(dict):
            response (list): List of response chunks (buffer).
            endpoint(str): The endpoint to use for the request.
            additional_data (Dict[str, Any]): Additional data to include in the response.

        Returns:
            tuple: (data, extra) where data is the processed raw data and extra is the formatted response.
        """

        if additional_data is None:
            additional_data = {}

        content, chunks = None, list()
        for lines in response:
            lines = lines.decode(encoding="utf-8").split(sep="\n\n")
            for line in lines:
                line = line.strip()
                if not line.startswith("data: "):
                    continue
                line = line.removeprefix("data: ")
                if not line:
                    continue
                try:
                    content = loads(line)
                    chunks.append(content)
                except JSONDecodeError as e:
                    logger.debug(f"Failed to decode JSON from streaming response ({e}) on the following chunk: {line}.")

        # error case
        if content is None:
            return None

        # normal case
        extra_chunk = content  # based on last chunk to conserve the chunk structure
        extra_chunk.update({"choices": []})
        extra_chunk.update(self._get_additional_data(json=json, data=chunks, stream=True, endpoint=endpoint, request_latency=request_latency))
        extra_chunk.update(additional_data)

        return extra_chunk

    async def forward_stream(
        self,
        method: str,
        endpoint: str,
        redis_client: AsyncRedis,
        json: dict | None = None,
        files: dict | None = None,
        data: dict | None = None,
        additional_data: dict[str, Any] | None = None,
    ):
        """
        Forward a stream request to a provider model and add model name to the response. Optionally, add additional data to the response.

        Args:
            method(str): The method to use for the request.
            endpoint(str): The endpoint to use for the request.
            redis_client(AsyncRedis): The redis client to use for the request.
            json(Optional[dict]): The JSON body to use for the request.
            files(Optional[dict]): The files to use for the request.
            data(Optional[dict]): The data to use for the request.
            additional_data(Dict[str, Any]): The additional data to add to the response (default: {}).
        """

        if additional_data is None:
            additional_data = {}

        url, json, files, data = self._format_request(json=json, files=files, data=data, endpoint=endpoint)

        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{self.id}"
            try:
                await redis_client.incr(inflight_key)
            except Exception:
                logger.error("Unable to increment redis requests inflight key")

            try:
                async with async_client.stream(method=method, url=url, headers=self.headers, json=json, files=files, data=data) as response:
                    buffer = list()
                    start_time = time.perf_counter()
                    first_token_time = None
                    async for chunk in response.aiter_raw():
                        # error case
                        if response.status_code // 100 != 2:
                            chunks = loads(chunk.decode(encoding="utf-8"))
                            if "message" in chunks:
                                try:
                                    chunks["message"] = ast.literal_eval(chunks["message"])
                                except Exception:
                                    pass
                            chunk = dumps(chunks).encode(encoding="utf-8")
                            yield chunk, response.status_code
                        # normal case
                        else:
                            match = re.search(rb"data: \[DONE\]", chunk)
                            if not match:
                                buffer.append(chunk)
                                if first_token_time is None:
                                    try:
                                        # The first token comes in the first non-empty chunk of the stream
                                        if loads((chunk.decode(encoding="utf-8")).removeprefix("data: "))["choices"][0]["delta"]["content"] != "":
                                            first_token_time = time.perf_counter()
                                    except Exception as e:
                                        logger.debug("Chunk data could not be processed to compute time to first token")

                                yield chunk, response.status_code

                            # end of the stream
                            else:
                                last_chunks = chunk[: match.start()]
                                done_chunk = chunk[match.start() :]

                                # Edge case: the stream consists in just one group of chunks
                                if first_token_time is None and last_chunks != "" and len(buffer) == 0:
                                    first_token_time = time.perf_counter()

                                buffer.append(last_chunks)

                                end_time = time.perf_counter()
                                request_latency = int((end_time - start_time) * 1000)  # ms
                                if first_token_time is not None:
                                    ttft = int((first_token_time - start_time) * 1000)  # ms
                                else:
                                    logger.warning(f"Time to first token could not be determined for request {request_context.get().id}.")
                                    ttft = None

                                extra_chunk = self._format_stream_response(
                                    json=json,
                                    response=buffer,
                                    endpoint=endpoint,
                                    additional_data=additional_data,
                                    request_latency=request_latency,
                                )
                                await self._log_performance_metric(redis_client=redis_client, ttft=ttft, latency=int(request_latency))

                                # if error case, yield chunk
                                if extra_chunk is None:
                                    yield chunk, response.status_code
                                    continue

                                yield last_chunks, response.status_code
                                yield f"data: {dumps(extra_chunk)}\n\n".encode(), response.status_code
                                yield done_chunk, response.status_code

            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                yield dumps({"detail": "Request timed out, model is too busy."}).encode(), 504
            except Exception as e:
                logger.error(traceback.format_exc())
                yield dumps({"detail": type(e).__name__}).encode(), 500
            finally:
                try:
                    await redis_client.decr(inflight_key)
                except Exception:
                    logger.error("Unable to decrement redis requests inflight key")
