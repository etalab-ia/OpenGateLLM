from http import HTTPMethod

from api.domain.chat.entities import ChatCompletion
from api.domain.provider.entities import ProviderEndpoint, ProviderRequest
from api.domain.provider.errors import ProviderAdapterValidationRequestError
from api.infrastructure.http._httpproviderrequest import HttpProviderRequest
from api.infrastructure.http.adapters import HttpProviderAdapter


class ChatCompletionsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = ProviderEndpoint.CHAT_COMPLETIONS
    TARGET_ENDPOINT_ROUTE = "/v1/chat/completions"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = ChatCompletion

    def to_http_request(self, request: ProviderRequest) -> HttpProviderRequest | ProviderAdapterValidationRequestError:
        match super().to_http_request(request):
            case HttpProviderRequest() as http_request:
                pass
            case error:
                return error

        if request.payload.stream:
            http_request.body["stream_options"] = {**(http_request.body.get("stream_options") or {}), "include_usage": True}

        return http_request
