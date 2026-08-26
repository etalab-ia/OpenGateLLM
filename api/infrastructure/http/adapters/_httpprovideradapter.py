from http import HTTPMethod
from typing import Annotated
from urllib.parse import urljoin
from uuid import uuid4

from pydantic import StringConstraints, ValidationError

from api.domain.provider import ProviderAdapter
from api.domain.provider.entities import Provider, ProviderRawResponse, ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.infrastructure.http import HttpProviderRequest
from api.utils.variables import EndpointRoute


class HttpProviderAdapter(ProviderAdapter):
    SOURCE_ENDPOINT: EndpointRoute
    TARGET_ENDPOINT_ROUTE: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True)]
    TARGET_ENDPOINT_METHOD: HTTPMethod
    RESPONSE_TYPE: type | None

    def __init__(self, provider: Provider):
        self.provider = provider

    def to_http_request(self, request: ProviderRequest) -> HttpProviderRequest | ProviderAdapterValidationRequestError:
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)
        http_request = HttpProviderRequest(
            method=self.TARGET_ENDPOINT_METHOD,
            url=target_url,
            body=request.payload.model_dump(exclude_none=True) if request.payload else {},
        )

        if "model" in http_request.body:
            http_request.body["model"] = self.provider.model_name

        return http_request

    def to_domain_response(
        self,
        raw_response: ProviderRawResponse,
        request: ProviderRequest,
    ) -> ProviderResponse | ProviderAdapterValidationResponseError:
        request_id = self._extract_request_id(raw_response=raw_response)
        try:
            data = self.RESPONSE_TYPE(**{**raw_response.data, "id": request_id, "model": request.payload.model})
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        return ProviderResponse(id=request_id, data=data)

    @staticmethod
    def _build_target_url(base_url: str, target_endpoint_route: str | None) -> str:
        base_url = base_url + "/" if not base_url.endswith("/") else base_url
        url = base_url if target_endpoint_route is None else urljoin(base=base_url, url=target_endpoint_route.lstrip("/"))
        return url

    @staticmethod
    def _extract_request_id(raw_response: ProviderRawResponse) -> str:
        default_request_id = f"request-{str(uuid4()).replace('-', '')}"

        if isinstance(raw_response.data, dict):
            return raw_response.data.get("id", default_request_id)

        return default_request_id
