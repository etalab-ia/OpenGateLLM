from http import HTTPMethod

from api.domain.chat.entities import ChatCompletion, ChatCompletionChunk
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class ChatCompletionsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.CHAT_COMPLETIONS
    TARGET_ENDPOINT_ROUTE = "/v1/chat/completions"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = ChatCompletion | ChatCompletionChunk
