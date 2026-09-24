from enum import StrEnum


class RouterName(StrEnum):
    ADMIN = ("admin", "api.infrastructure.fastapi.endpoints.admin")
    AUDIO = ("audio", "api.infrastructure.fastapi.endpoints.audio")
    AUTH = ("auth", "api.infrastructure.fastapi.endpoints.auth")
    CHAT = ("chat", "api.infrastructure.fastapi.endpoints.chat")
    EMBEDDINGS = ("embeddings", "api.infrastructure.fastapi.endpoints.embeddings")
    HEALTH = ("health", "api.infrastructure.fastapi.endpoints.health")
    KEYS = ("keys", "api.infrastructure.fastapi.endpoints.keys")
    ME = ("me", "api.infrastructure.fastapi.endpoints.me")
    MODELS = ("models", "api.infrastructure.fastapi.endpoints.models")
    MONITORING = ("monitoring", "api.infrastructure.fastapi.endpoints.health")
    OCR = ("ocr", "api.infrastructure.fastapi.endpoints.ocr")
    ORGANIZATIONS = ("organizations", "api.infrastructure.fastapi.endpoints.organizations")
    RERANK = ("rerank", "api.infrastructure.fastapi.endpoints.rerank")
    USAGE = ("usage", "api.infrastructure.fastapi.endpoints.usage")

    def __new__(cls, value: str, module_path: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.module_path = module_path

        return obj


class EndpointRoute(StrEnum):
    ADMIN_ORGANIZATIONS = "/admin/organizations"
    ADMIN_PROVIDERS = "/admin/providers"
    ADMIN_ROLES = "/admin/roles"
    ADMIN_ROUTERS = "/admin/routers"
    ADMIN_KEYS = "/admin/keys"
    ADMIN_USERS = "/admin/users"
    AUDIO_TRANSCRIPTIONS = "/audio/transcriptions"
    AUTH_LOGIN = "/auth/login"
    AUTH_SSO_LOGIN = "/auth/sso/login"
    CHAT_COMPLETIONS = "/chat/completions"
    EMBEDDINGS = "/embeddings"
    HEALTH = "/health"
    HEALTH_MODELS = "/health/models"
    KEYS = "/keys"
    ME = "/me"
    ME_USAGE = "/me/usage"
    METRICS = "/metrics"
    MODELS = "/models"
    OCR = "/ocr"
    ORGANIZATIONS_ME = "/organizations/me"
    RERANK = "/rerank"
    USAGE = "/usage"
