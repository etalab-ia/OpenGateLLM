import datetime as dt

import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.routers.models import Router
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState


class RoutersState(EntityState):
    """Routers management state."""

    @rx.var
    def router_types_list(self) -> list[str]:
        """Get list of router types."""
        return ["image-text-to-text", "automatic-speech-recognition", "text-embeddings-inference", "text-generation", "text-classification"]

    @rx.var
    def router_load_balancing_strategies_list(self) -> list[str]:
        """Get list of router load balancing strategies."""
        return ["Shuffle", "Least busy"]

    ############################################################
    # Load entities
    ############################################################
    entities: list[Router] = []
    router_owners: dict[int, str] = {}

    def _format_router(self, router: dict) -> Router:
        """Format router."""

        _load_balancing_strategy_converter = {
            "shuffle": "Shuffle",
            "least_busy": "Least Busy",
        }
        return Router(
            id=router["id"],
            name=router["name"],
            user=self.router_owners[router["user_id"]],
            type=router["type"],
            aliases=",".join(router["aliases"]) if router["aliases"] else "",
            load_balancing_strategy=_load_balancing_strategy_converter.get(router["load_balancing_strategy"]),
            max_context_length=router["max_context_length"],
            vector_size=router["vector_size"],
            cost_prompt_tokens=router["cost_prompt_tokens"],
            cost_completion_tokens=router["cost_completion_tokens"],
            providers=router["providers"],
            created=dt.datetime.fromtimestamp(router["created"]).strftime("%Y-%m-%d %H:%M"),
            updated=dt.datetime.fromtimestamp(router["updated"]).strftime("%Y-%m-%d %H:%M"),
        )

    @rx.var
    def routers(self) -> list[Router]:
        """Get routers list with correct typing for Reflex."""
        return self.entities

    @rx.event
    async def load_entities(self):
        """Load entities."""
        if not self.is_authenticated or not self.api_key:
            return

        self.entities_loading = True
        yield

        params = {
            "offset": (self.page - 1) * self.per_page,
            "limit": self.per_page,
            "order_by": self.order_by_value,
            "order_direction": self.order_direction_value,
        }

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/routers",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )

                response.raise_for_status()
                data = response.json()
                self.entities = []

                for router in data.get("data", []):
                    if router["user_id"] not in self.router_owners:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                url=f"{self.opengatellm_url}/v1/admin/users/{router["user_id"]}",
                                headers={"Authorization": f"Bearer {self.api_key}"},
                                timeout=configuration.settings.playground_opengatellm_timeout,
                            )
                            if response.status_code == 404:
                                self.router_owners[router["user_id"]] = "Master"
                            elif response.status_code == 200:
                                data = response.json()
                                self.router_owners[router["user_id"]] = data.get("name", "Unknown")
                            else:
                                self.router_owners[router["user_id"]] = "Unknown"

                    self.entities.append(self._format_router(router))

            self.has_more_page = len(self.entities) == self.per_page
        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.entities_loading = False
            yield

    ############################################################
    # Delete entity
    ############################################################
    entity_to_delete: Router = Router()

    @rx.event
    def set_entity_to_delete(self, entity: Router):
        """Set entity to delete."""
        self.entity_to_delete = entity

    @rx.var
    def is_delete_entity_dialog_open(self) -> bool:
        """Check if delete dialog should be open."""
        return self.entity_to_delete.id is not None

    @rx.event
    def handle_delete_entity_dialog_change(self, is_open: bool):
        """Handle delete entity dialog open/close state change."""
        if not is_open:
            self.entity_to_delete = Router()

    async def delete_entity(self):
        """Delete a router."""
        self.delete_entity_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/admin/routers/{self.entity_to_delete.id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                self.handle_delete_entity_dialog_change(is_open=False)
                yield rx.toast.success("Router deleted successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.delete_entity_loading = False
            yield

    ############################################################
    # Create entity
    ############################################################
    entity_to_create: Router = Router(
        type="text-generation",
        load_balancing_strategy="Shuffle",
        cost_prompt_tokens=0.0,
        cost_completion_tokens=0.0,
    )

    @rx.event
    def set_new_entity_attribut(self, attribute: str, value: str | bool | None):
        """Set new entity attributes."""
        if isinstance(value, str):
            setattr(self.entity_to_create, attribute, value.strip())
        else:
            setattr(self.entity_to_create, attribute, value)

    @rx.event
    async def create_entity(self):
        """Create a router."""
        if not self.entity_to_create.name:
            yield rx.toast.warning("Router is required", position="bottom-right")
            return

        self.create_entity_loading = True
        yield

        new_router_load_balancing_strategy = self.entity_to_create.load_balancing_strategy.lower().replace(" ", "_")

        payload = {
            "name": self.entity_to_create.name,
            "type": self.entity_to_create.type,
            "load_balancing_strategy": new_router_load_balancing_strategy,
            "cost_prompt_tokens": self.entity_to_create.cost_prompt_tokens,
            "cost_completion_tokens": self.entity_to_create.cost_completion_tokens,
        }

        if self.entity_to_create.aliases:
            new_router_aliases = [alias.strip() for alias in self.entity_to_create.aliases.split(",") if alias.strip()]
            if new_router_aliases:
                payload["aliases"] = new_router_aliases

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/admin/routers",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                yield rx.toast.success("Router created successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.create_entity_loading = False
            yield

    ############################################################
    # Entity settings
    ############################################################
    entity: Router = Router()

    @rx.event
    def set_entity_settings(self, entity: Router):
        """Set entity settings."""
        self.entity = entity

    @rx.event
    def set_edit_entity_attribut(self, attribute: str, value: str | bool | None):
        """Set edit entity attributes."""
        if isinstance(value, str):
            setattr(self.entity, attribute, value.strip())
        else:
            setattr(self.entity, attribute, value)

    @rx.var
    def is_settings_entity_dialog_open(self) -> bool:
        """Check if settings dialog should be open."""
        return self.entity.id is not None

    @rx.event
    def handle_settings_entity_dialog_change(self, is_open: bool):
        """Handle settings dialog open/close state change."""
        if not is_open:
            self.entity = Router()

    @rx.event
    async def edit_entity(self):
        """Update a router."""
        self.edit_entity_loading = True
        yield

        router_aliases = [alias.strip() for alias in self.entity.aliases.split(",") if alias.strip()]
        router_load_balancing_strategy = self.entity.load_balancing_strategy.lower().replace(" ", "_")

        payload = {
            "name": self.entity.name,
            "type": self.entity.type,
            "aliases": router_aliases,
            "load_balancing_strategy": router_load_balancing_strategy,
            "cost_prompt_tokens": self.entity.cost_prompt_tokens,
            "cost_completion_tokens": self.entity.cost_completion_tokens,
        }

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/admin/routers/{self.entity.id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
            response.raise_for_status()

            self.handle_settings_entity_dialog_change(is_open=False)
            yield rx.toast.success("Router updated successfully", position="bottom-right")

            async for _ in self.load_entities():
                yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.edit_entity_loading = False
            yield

    ############################################################
    # Pagination & filters
    ############################################################
    per_page: int = 20
    order_by_options: list[str] = ["id", "name", "created"]

    @rx.event
    async def set_order_by(self, value: str):
        """Set order by field and reload."""
        self.order_by_value = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_entities():
            yield

    @rx.event
    async def set_order_direction(self, value: str):
        """Set order direction and reload."""
        self.order_direction_value = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_entities():
            yield

    @rx.event
    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            yield
            async for _ in self.load_entities():
                yield

    @rx.event
    async def next_page(self):
        if self.has_more_page:
            self.page += 1
            yield
            async for _ in self.load_entities():
                yield
