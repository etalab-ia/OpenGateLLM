from http import HTTPMethod

from api.domain.chat.entities import ChatCompletion
from api.domain.provider.entities import ProviderEndpoint
from api.infrastructure.http.adapters import HttpProviderAdapter


class ChatCompletionsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = ProviderEndpoint.CHAT_COMPLETIONS
    TARGET_ENDPOINT_ROUTE = "/v1/chat/completions"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = ChatCompletion
