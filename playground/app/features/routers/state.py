import datetime as dt

import httpx
import reflex as rx

from app.features.routers.models import Router
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
            vector_size=router["vector_size"],
            max_context_length=router["max_context_length"],
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

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/routers",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
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
                                timeout=60.0,
                            )
                            if response.status_code == 404:
                                self.router_owners[router["user_id"]] = "Master"
                            elif response.status_code == 200:
                                data = response.json()
                                self.router_owners[router["user_id"]] = data.get("name", "Unknown")
                            else:
                                self.router_owners[router["user_id"]] = "Unknown"

                    self.entities.append(self._format_router(router))

        except Exception as e:
            yield rx.toast.error(f"Error loading providers: {str(e)}", position="bottom-right")
        finally:
            self.entities_loading = False
            yield

    ############################################################
    # Delete entity
    ############################################################
    @rx.event
    async def delete_entity(self):
        """Delete a router."""
        self.delete_entity_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/admin/routers/{self.delete_entity_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
                response.raise_for_status()

                self.handle_delete_entity_dialog_change(is_open=False)
                yield rx.toast.success("Router deleted successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield rx.toast.error(f"Error deleting router: {str(e)}", position="bottom-right")
        finally:
            self.delete_entity_loading = False
            yield

    ############################################################
    # Create entity
    ############################################################
    new_router_name: str = ""
    new_router_type: str = "text-generation"
    new_router_aliases: str = ""
    new_router_load_balancing_strategy: str = "Shuffle"
    new_router_cost_prompt_tokens: float = 0.0
    new_router_cost_completion_tokens: float = 0.0

    @rx.event
    async def create_entity(self):
        """Create a router."""
        if not self.new_router_name:
            yield rx.toast.warning("Router is required", position="bottom-right")
            return

        self.create_entity_loading = True
        yield

        new_router_load_balancing_strategy = self.new_router_load_balancing_strategy.lower().replace(" ", "_")

        payload = {
            "name": self.new_router_name,
            "type": self.new_router_type,
            "load_balancing_strategy": new_router_load_balancing_strategy,
            "cost_prompt_tokens": self.new_router_cost_prompt_tokens,
            "cost_completion_tokens": self.new_router_cost_completion_tokens,
        }

        new_router_aliases = [alias.strip() for alias in self.new_router_aliases.split(",") if alias.strip()]
        if new_router_aliases:
            payload["aliases"] = new_router_aliases

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/admin/routers",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
                response.raise_for_status()

                yield rx.toast.success("Router created successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield rx.toast.error(f"Error creating router: {str(e)}", position="bottom-right")
        finally:
            self.create_entity_loading = False
            yield

    @rx.event
    def set_new_router_name(self, value: str):
        """Set new router name."""
        self.new_router_name = value.strip()

    @rx.event
    def set_new_router_type(self, value: str):
        """Set new router type."""
        self.new_router_type = value

    @rx.event
    def set_new_router_aliases(self, value: str):
        """Set new router aliases."""
        self.new_router_aliases = value.strip()

    @rx.event
    def set_new_router_load_balancing_strategy(self, value: str):
        """Set new router load balancing strategy."""
        self.new_router_load_balancing_strategy = value

    @rx.event
    def set_new_router_cost_prompt_tokens(self, value: str):
        """Set new router cost prompt tokens."""
        self.new_router_cost_prompt_tokens = value

    @rx.event
    def set_new_router_cost_completion_tokens(self, value: str):
        """Set new router cost completion tokens."""
        self.new_router_cost_completion_tokens = value

    ############################################################
    # Edit entity
    ############################################################

    edit_entity_id = None
    edit_router_name: str = ""
    edit_router_type: str = "text-generation"
    edit_router_aliases: str = ""
    edit_router_load_balancing_strategy: str = "Shuffle"
    edit_router_cost_prompt_tokens: float = 0.0
    edit_router_cost_completion_tokens: float = 0.0

    @rx.event
    def set_entity_to_edit(self, entity: Router):
        """Set entity to edit and load its data."""
        self.edit_entity_id = entity.id
        self.edit_router_name = entity.name
        self.edit_router_type = entity.type
        self.edit_router_aliases = entity.aliases
        self.edit_router_load_balancing_strategy = entity.load_balancing_strategy
        self.edit_router_cost_prompt_tokens = entity.cost_prompt_tokens
        self.edit_router_cost_completion_tokens = entity.cost_completion_tokens

    @rx.event
    async def update_entity(self):
        """Update a router."""
        self.edit_entity_loading = True
        yield

        edit_router_aliases = [alias.strip() for alias in self.edit_router_aliases.split(",") if alias.strip()]
        edit_router_load_balancing_strategy = self.edit_router_load_balancing_strategy.lower().replace(" ", "_")

        payload = {
            "name": self.edit_router_name,
            "type": self.edit_router_type,
            "aliases": edit_router_aliases,
            "load_balancing_strategy": edit_router_load_balancing_strategy,
            "cost_prompt_tokens": self.edit_router_cost_prompt_tokens,
            "cost_completion_tokens": self.edit_router_cost_completion_tokens,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/admin/routers/{self.edit_entity_id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
            response.raise_for_status()

            self.handle_edit_entity_dialog_change(is_open=False)
            yield rx.toast.success("Router updated successfully", position="bottom-right")

            async for _ in self.load_entities():
                yield

        except Exception as e:
            yield rx.toast.error(f"Error updating router: {str(e)}", position="bottom-right")
        finally:
            self.edit_entity_loading = False
            yield

    @rx.event
    def set_edit_router_name(self, value: str):
        """Set new router name."""
        self.edit_entity.name = value.strip()

    @rx.event
    def set_edit_router_type(self, value: str):
        """Set new router type."""
        self.edit_entity.type = value

    @rx.event
    def set_edit_router_aliases(self, value: str):
        """Set new router aliases."""
        self.edit_entity.aliases = value.strip()

    @rx.event
    def set_edit_router_load_balancing_strategy(self, value: str):
        """Set new router load balancing strategy."""
        self.edit_entity.load_balancing_strategy = value

    @rx.event
    def set_edit_router_cost_prompt_tokens(self, value: str):
        """Set new router cost prompt tokens."""
        self.edit_entity.cost_prompt_tokens = value

    @rx.event
    def set_edit_router_cost_completion_tokens(self, value: str):
        """Set new router cost completion tokens."""
        self.edit_entity.cost_completion_tokens = value
