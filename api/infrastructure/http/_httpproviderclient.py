import ast
from json import JSONDecodeError, loads
import logging

import httpx
from httpx import BasicAuth

from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider import ProviderAdapterBuilder, ProviderClient, ProviderClientResponse
from api.domain.provider.entities import Provider, ProviderRawResponse, ProviderRequest
from api.domain.provider.errors import ProviderAdapterValidationRequestError, UnsupportedProviderEndpointError
from api.infrastructure.http.adapters import HttpProviderAdapter

from ._httpproviderrequest import HttpProviderRequest

logger = logging.getLogger(__name__)


class HttpProviderClient(ProviderClient):
    def __init__(self, adapter_builder: ProviderAdapterBuilder):
        self.adapter_builder = adapter_builder

    async def forward(self, provider: Provider, request: ProviderRequest) -> ProviderClientResponse:
        adapter = self.adapter_builder.build(endpoint=request.endpoint, provider=provider)
        match adapter:
            case UnsupportedProviderEndpointError() as error:
                return error
            case HttpProviderAdapter() as adapter:
                pass

        http_request = adapter.to_http_request(request)
        match http_request:
            case ProviderAdapterValidationRequestError() as error:
                return error
            case HttpProviderRequest() as http_request:
                pass

        return await self._send(provider=provider, http_request=http_request)

    async def _send(self, provider: Provider, http_request: HttpProviderRequest) -> ProviderClientResponse:
        # TEMPORARY PATCH FOR MISTRAL METRICS ENDPOINT
        auth = BasicAuth(username=http_request.auth.username, password=http_request.auth.password) if http_request.auth else None

        async with httpx.AsyncClient(timeout=provider.timeout) as async_client:
            try:
                response = await async_client.request(
                    headers={"Authorization": f"Bearer {provider.key}"} if provider.key else {},
                    auth=auth,
                    method=http_request.method,
                    url=http_request.url,
                    json=http_request.body,
                    files=http_request.files,
                    data=http_request.form,
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

        if response.headers.get("Content-Type") == "application/json":
            data, text = response.json(), None
        else:
            data, text = None, response.text

        return ProviderRawResponse(data=data, text=text)

    async def forward_stream(self, provider: Provider, request: ProviderRequest):
        raise NotImplementedError()
