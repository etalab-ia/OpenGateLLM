from dataclasses import dataclass

from api.utils.variables import RouterName


@dataclass(frozen=True)
class RouterDefinition:
    name: str
    module_path: str


ROUTER_DEFINITIONS: tuple[RouterDefinition, ...] = (
    # Admin routers
    RouterDefinition(name=RouterName.ADMIN, module_path="api.endpoints.admin.organizations"),
    RouterDefinition(name=RouterName.ADMIN, module_path="api.infrastructure.fastapi.endpoints.admin.providers"),
    RouterDefinition(name=RouterName.ADMIN, module_path="api.endpoints.admin.roles"),
    RouterDefinition(name=RouterName.ADMIN, module_path="api.endpoints.admin.routers"),
    RouterDefinition(name=RouterName.ADMIN, module_path="api.infrastructure.fastapi.endpoints.admin_router"),
    RouterDefinition(name=RouterName.ADMIN, module_path="api.endpoints.admin.tokens"),
    RouterDefinition(name=RouterName.ADMIN, module_path="api.endpoints.admin.users"),
    # Core routers
    RouterDefinition(name=RouterName.AUDIO, module_path="api.endpoints.audio"),
    RouterDefinition(name=RouterName.AUTH, module_path="api.endpoints.auth"),
    RouterDefinition(name=RouterName.CHAT, module_path="api.endpoints.chat"),
    RouterDefinition(name=RouterName.CHUNKS, module_path="api.endpoints.chunks"),
    RouterDefinition(name=RouterName.COLLECTIONS, module_path="api.endpoints.collections"),
    RouterDefinition(name=RouterName.DOCUMENTS, module_path="api.endpoints.documents"),
    RouterDefinition(name=RouterName.EMBEDDINGS, module_path="api.endpoints.embeddings"),
    RouterDefinition(name=RouterName.MODELS, module_path="api.infrastructure.fastapi.endpoints.models"),
    RouterDefinition(name=RouterName.OCR, module_path="api.endpoints.ocr"),
    RouterDefinition(name=RouterName.PARSE, module_path="api.endpoints.parse"),
    RouterDefinition(name=RouterName.RERANK, module_path="api.endpoints.rerank"),
    RouterDefinition(name=RouterName.SEARCH, module_path="api.endpoints.search"),
    # Me routers
    RouterDefinition(name=RouterName.ME, module_path="api.endpoints.me.info"),
    RouterDefinition(name=RouterName.ME, module_path="api.endpoints.me.keys"),
    RouterDefinition(name=RouterName.ME, module_path="api.endpoints.me.usage"),
)
