from pydantic import BaseModel, ConfigDict

from api.schemas.me.info import UserInfo
from api.utils.context import request_context

# @TODO: instanciate the request_context here


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    # request identifiers
    id: str | None = None
    method: str | None = None
    endpoint: str | None = None

    # request context
    user_info: UserInfo | None = None
    user_id: int | None = None
    key_id: int | None = None
    key_name: str | None = None


class RequestContextManager:
    def get_request_context(self):
        return request_context.get()

    def get_usage(self):
        return request_context.get().usage

    def get_ttft(self):
        return request_context.get().ttft

    def get_request_id(self):
        return request_context.get().id

    def get_latency(self):
        return request_context.get().latency

    def set_usage(self, usage):
        request_context.get().usage = usage

    def set_ttft(self, ttft):
        request_context.get().ttft = ttft

    def set_request_id(self, request_id):
        request_context.get().id = request_id

    def set_latency(self, latency):
        request_context.get().latency = latency
