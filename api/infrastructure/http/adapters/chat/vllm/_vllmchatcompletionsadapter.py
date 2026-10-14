from api.domain.provider.entities import ProviderRequest
from api.domain.provider.errors import ProviderAdapterValidationRequestError
from api.infrastructure.http._httpproviderrequest import HttpProviderRequest
from api.infrastructure.http.adapters.chat import ChatCompletionsAdapter


class VllmChatCompletionsAdapter(ChatCompletionsAdapter):
    def to_http_request(self, request: ProviderRequest) -> HttpProviderRequest | ProviderAdapterValidationRequestError:
        match super().to_http_request(request):
            case HttpProviderRequest() as http_request:
                pass
            case error:
                return error

        if request.payload.stream:
            http_request.body["stream_options"] = {**(http_request.body.get("stream_options") or {}), "include_usage": True}

        return http_request
