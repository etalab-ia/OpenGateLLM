import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.collections.models import Collection
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState
from app.shared.utils.timestamps import format_datetime


class CollectionsState(EntityState):
    """Browse and manage collections through OpenGateRAG."""

    entities: list[Collection] = []
    opengaterag_url: str = configuration.settings.playground_opengaterag_url
    load_error: str = ""
    search_input: str = ""
    search: str = ""
    visibility_filter: str = "all"
    visibility_options: list[str] = ["all", "private", "public"]
    page: int = 1
    per_page: int = 12
    has_next_page: bool = False
    order_by_value: str = "updated"
    order_by_options: list[str] = ["id", "name", "created", "updated"]
    order_direction_value: str = "desc"
    order_direction_options: list[str] = ["asc", "desc"]

    @rx.var
    def collections(self) -> list[Collection]:
        return self.entities

    @rx.var
    def total_pages(self) -> int:
        return self.page + int(self.has_next_page)

    def _format_collection(self, collection: dict) -> Collection:
        return Collection(
            id=collection["id"],
            name=collection["name"],
            description=collection.get("description") or "",
            owner=collection["owner"],
            visibility=collection.get("visibility") or "private",
            documents=collection.get("documents", 0),
            size=collection.get("size", 0),
            created=format_datetime(collection["created"]),
            updated=format_datetime(collection["updated"]),
            is_owner=collection["owner"] == self.user_id,
        )

    def _error_message(self, response: httpx.Response | None) -> str:
        if response is None:
            return "Collections could not be loaded. Check your connection and try again."
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        if isinstance(detail, str) and detail:
            return detail
        return f"Collections could not be loaded (HTTP {response.status_code}). Try again."

    @rx.event
    async def load_entities(self):
        if not self.is_authenticated or not self.api_key:
            return

        self.entities_loading = True
        self.load_error = ""
        yield

        params = {
            "offset": (self.page - 1) * self.per_page,
            "limit": self.per_page + 1,
            "order_by": self.order_by_value,
            "order_direction": self.order_direction_value,
        }
        if self.search:
            params["name"] = self.search
        if self.visibility_filter != "all":
            params["visibility"] = self.visibility_filter

        response = None
        try:
            response = await self._request("GET", "/v1/collections", params=params)
            response.raise_for_status()
            data = response.json().get("data", [])
            self.has_next_page = len(data) > self.per_page
            self.entities = [self._format_collection(item) for item in data[: self.per_page]]
        except Exception as e:
            self.entities = []
            self.has_next_page = False
            self.load_error = self._error_message(response)
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.entities_loading = False
            yield

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.request(
                method,
                f"{self.opengaterag_url.rstrip('/')}{path}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.opengatellm_timeout,
                **kwargs,
            )

    @rx.event
    def set_search_input(self, value: str):
        self.search_input = value

    @rx.event
    async def submit_search(self):
        self.search = self.search_input.strip()
        self.page = 1
        async for event in self.load_entities():
            yield event

    @rx.event
    async def clear_search(self):
        self.search_input = ""
        self.search = ""
        self.page = 1
        async for event in self.load_entities():
            yield event

    @rx.event
    async def set_visibility_filter(self, value: str):
        self.visibility_filter = value
        self.page = 1
        async for event in self.load_entities():
            yield event

    @rx.event
    async def set_order_by(self, value: str):
        self.order_by_value = value
        self.page = 1
        async for event in self.load_entities():
            yield event

    @rx.event
    async def set_order_direction(self, value: str):
        self.order_direction_value = value
        self.page = 1
        async for event in self.load_entities():
            yield event

    @rx.event
    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            async for event in self.load_entities():
                yield event

    @rx.event
    async def next_page(self):
        if self.has_next_page:
            self.page += 1
            async for event in self.load_entities():
                yield event

    entity_to_create: Collection = Collection()
    is_create_dialog_open: bool = False

    @rx.event
    def open_create_dialog(self):
        self.entity_to_create = Collection()
        self.is_create_dialog_open = True

    @rx.event
    def handle_create_dialog_change(self, is_open: bool):
        if not self.create_entity_loading:
            self.is_create_dialog_open = is_open

    @rx.event
    def set_new_entity_attribut(self, attribute: str, value: str | bool | None):
        setattr(self.entity_to_create, attribute, value)

    @rx.event
    async def create_entity(self):
        if not self.entity_to_create.name.strip():
            yield rx.toast.warning("Name is required", position="bottom-right")
            return
        self.create_entity_loading = True
        yield

        payload = {
            "name": self.entity_to_create.name.strip(),
            "description": self.entity_to_create.description.strip() or None,
            "visibility": self.entity_to_create.visibility,
        }
        response = None
        try:
            response = await self._request("POST", "/v1/collections", json=payload)
            response.raise_for_status()
            self.is_create_dialog_open = False
            self.entity_to_create = Collection()
            yield rx.toast.success("Collection created", position="bottom-right")
            async for event in self.load_entities():
                yield event
        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.create_entity_loading = False
            yield

    entity: Collection = Collection()

    @rx.var
    def is_settings_entity_dialog_open(self) -> bool:
        return self.entity.id is not None

    @rx.event
    def set_entity_settings(self, entity: Collection):
        if entity.is_owner:
            self.entity = entity.model_copy(deep=True)

    @rx.event
    def handle_settings_entity_dialog_change(self, is_open: bool):
        if not is_open and not self.edit_entity_loading:
            self.entity = Collection()

    @rx.event
    def set_edit_entity_attribut(self, attribute: str, value: str | bool | None):
        setattr(self.entity, attribute, value)

    @rx.event
    async def edit_entity(self):
        if not self.entity.is_owner or self.entity.owner != self.user_id:
            yield rx.toast.error("Only the owner can edit this collection", position="bottom-right")
            return
        if not self.entity.name.strip():
            yield rx.toast.warning("Name is required", position="bottom-right")
            return
        self.edit_entity_loading = True
        yield

        payload = {"name": self.entity.name.strip(), "description": self.entity.description.strip(), "visibility": self.entity.visibility}
        response = None
        try:
            response = await self._request("PATCH", f"/v1/collections/{self.entity.id}", json=payload)
            response.raise_for_status()
            self.entity = Collection()
            yield rx.toast.success("Collection updated", position="bottom-right")
            async for event in self.load_entities():
                yield event
        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.edit_entity_loading = False
            yield

    entity_to_delete: Collection = Collection()

    @rx.var
    def is_delete_entity_dialog_open(self) -> bool:
        return self.entity_to_delete.id is not None

    @rx.event
    def set_entity_to_delete(self, entity: Collection):
        if entity.is_owner:
            self.entity_to_delete = entity

    @rx.event
    def handle_delete_entity_dialog_change(self, is_open: bool):
        if not is_open and not self.delete_entity_loading:
            self.entity_to_delete = Collection()

    @rx.event
    async def delete_entity(self):
        if not self.entity_to_delete.is_owner or self.entity_to_delete.owner != self.user_id:
            yield rx.toast.error("Only the owner can delete this collection", position="bottom-right")
            return
        self.delete_entity_loading = True
        yield

        response = None
        try:
            response = await self._request("DELETE", f"/v1/collections/{self.entity_to_delete.id}")
            response.raise_for_status()
            self.entity_to_delete = Collection()
            if len(self.entities) == 1 and self.page > 1:
                self.page -= 1
            yield rx.toast.success("Collection deleted", position="bottom-right")
            async for event in self.load_entities():
                yield event
        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.delete_entity_loading = False
            yield
