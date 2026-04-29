import ast
from json import JSONDecodeError, loads
import logging
import time

import httpx

from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider import ProviderClient, ProviderMetricsLogger
from api.domain.provider.entities import Provider, ProviderFormattedRequest, ProviderOriginalResponse

logger = logging.getLogger(__name__)

type HttpProviderClientResponse = ProviderOriginalResponse | TooBusyModelError | UnknownModelError | StatusCodeModelError


class HttpProviderClient(ProviderClient):
    def __init__(self, provider_metrics_logger: ProviderMetricsLogger | None = None):
        self.provider_metrics_logger = provider_metrics_logger

    def log_metrics(func):
        async def wrapper(self, *args, **kwargs):
            if self.provider_metrics_logger is None:
                return await func(self, *args, **kwargs)

            provider = kwargs.get("provider")
            inflight_is_incremented = await self.provider_metrics_logger.increment_inflight(provider_id=provider.id)
            try:
                response = await func(self, *args, **kwargs)
                return response
            finally:
                match response:
                    case ProviderOriginalResponse() as response:
                        await self.provider_metrics_logger.log_latency(provider_id=provider.id, latency=response.latency)
                    case TooBusyModelError() | UnknownModelError():
                        await self.provider_metrics_logger.log_error(provider_id=provider.id)
                await self.provider_metrics_logger.decrement_inflight(provider_id=provider.id, inflight_is_incremented=inflight_is_incremented)

        return wrapper

    @log_metrics
    async def forward_request(self, provider: Provider, formatted_request: ProviderFormattedRequest) -> HttpProviderClientResponse:
        async with httpx.AsyncClient(timeout=provider.timeout) as async_client:
            start_time = time.perf_counter()
            try:
                response = await async_client.request(
                    headers={"Authorization": f"Bearer {provider.key}"} if provider.key else {},
                    method=formatted_request.method,
                    url=formatted_request.url,
                    json=formatted_request.body,
                    files=formatted_request.files,
                    data=formatted_request.form,
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
                return TooBusyModelError(status_code=500, detail=type(e).__name__)
            except Exception as e:
                logger.exception(msg=f"Failed to forward request to {provider.model_name}.")
                return UnknownModelError(status_code=500, detail=str(e))

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
                    message = response.text
                return StatusCodeModelError(status_code=response.status_code, detail=message)

        latency = self._elapsed_ms(start_time=start_time)

        if response.headers.get("Content-Type") == "application/json":
            data, text = response.json(), None
        else:
            data, text = None, response.text

        return ProviderOriginalResponse(data=data, text=text, latency=latency)

    @log_metrics
    async def forward_stream(self, provider: Provider, formatted_request: ProviderFormattedRequest):
        raise NotImplementedError()

    @staticmethod
    def _elapsed_ms(start_time: float) -> int:
        return int((time.perf_counter() - start_time) * 1000)  # ms
