from http import HTTPMethod
from typing import Annotated
from urllib.parse import urljoin
from uuid import uuid4

from pydantic import StringConstraints, ValidationError

from api.domain.provider import ProviderAdapter
from api.domain.provider.entities import (
    Provider,
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalRequest,
    ProviderOriginalResponse,
)
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.utils.variables import EndpointRoute


class HttpProviderAdapter(ProviderAdapter):
    SOURCE_ENDPOINT: EndpointRoute
    TARGET_ENDPOINT_ROUTE: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True)]
    TARGET_ENDPOINT_METHOD: HTTPMethod
    RESPONSE_TYPE: type | None

    def __init__(self, provider: Provider):
        self.provider = provider

    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest | ProviderAdapterValidationRequestError:
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)
        formatted_request = ProviderFormattedRequest(
            method=self.TARGET_ENDPOINT_METHOD,
            url=target_url,
            body=original_request.payload.model_dump(exclude_none=True) if original_request.payload else {},
        )

        if "model" in formatted_request.body:
            formatted_request.body["model"] = self.provider.model_name

        return formatted_request

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
    ) -> ProviderFormattedResponse | ProviderAdapterValidationResponseError:
        request_id = self._extract_request_id(original_response=original_response)
        try:
            data = self.RESPONSE_TYPE(**{**original_response.data, "id": request_id, "model": original_request.payload.model})
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        return ProviderFormattedResponse(id=request_id, data=data)

    @staticmethod
    def _build_target_url(base_url: str, target_endpoint_route: str | None) -> str:
        base_url = base_url + "/" if not base_url.endswith("/") else base_url
        url = base_url if target_endpoint_route is None else urljoin(base=base_url, url=target_endpoint_route.lstrip("/"))
        return url

    @staticmethod
    def _extract_request_id(original_response: ProviderOriginalResponse) -> str:
        default_request_id = f"request-{str(uuid4()).replace('-', '')}"

        if isinstance(original_response.data, dict):
            return original_response.data.get("id", default_request_id)

        return default_request_id
