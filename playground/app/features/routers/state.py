import datetime as dt

import httpx
import reflex as rx

from app.features.routers.models import Router
from app.shared.states.entity_state import EntityState


class RoutersState(EntityState):
    """Routers management state."""

    ############################################################
    # load entities
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
            aliases=router["aliases"],
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
    # delete entity
    ############################################################
    @rx.event
    async def delete_entity(self, entity_id: int):
        """Delete a router."""
        self.delete_entity_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/admin/routers/{entity_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
                response.raise_for_status()

                self.set_entity_to_delete(None)
                yield rx.toast.success("Router deleted successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield rx.toast.error(f"Error deleting router: {str(e)}", position="bottom-right")
        finally:
            self.delete_entity_loading = False
            yield

    ############################################################
    # create entity
    ############################################################

    router_name: str = ""
    router_type: str = ""
    router_aliases: str = ""
    router_load_balancing_strategy: str = "Shuffle"
    router_cost_prompt_tokens: float = 0.0
    router_cost_completion_tokens: float = 0.0

    @rx.var
    def router_types_list(self) -> list[str]:
        """Get list of router types."""
        return ["image-text-to-text", "automatic-speech-recognition", "text-embeddings-inference", "text-generation", "text-classification"]

    @rx.var
    def router_load_balancing_strategies_list(self) -> list[str]:
        """Get list of router load balancing strategies."""
        return ["Shuffle", "Least busy"]

    @rx.event
    async def create_entity(self):
        """Create a router."""
        if not self.router_name:
            yield rx.toast.warning("Router is required", position="bottom-right")
            return

        if not self.router_type:
            yield rx.toast.warning("Router type is required", position="bottom-right")
            return

        self.create_entity_loading = True
        yield

        payload = {
            "name": self.router_name,
            "type": self.router_type,
            "aliases": self.router_aliases,
            "load_balancing_strategy": self.router_load_balancing_strategy.lower(),
            "cost_prompt_tokens": self.router_cost_prompt_tokens,
            "cost_completion_tokens": self.router_cost_completion_tokens,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/admin/routers",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
                response.raise_for_status()

                self.set_entity_to_create(None)
                yield rx.toast.success("Router created successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield rx.toast.error(f"Error creating router: {str(e)}", position="bottom-right")
        finally:
            self.create_entity_loading = False
            yield

    @rx.event
    def set_router_name(self, value: str):
        """Set new router name."""
        self.router_name = value.strip()

    @rx.event
    def set_router_type(self, value: str):
        """Set new router type."""
        self.router_type = value

    @rx.event
    def set_router_aliases(self, value: str):
        """Set new router aliases."""
        self.router_aliases = [alias.strip() for alias in value if alias.strip()]

    @rx.event
    def set_router_load_balancing_strategy(self, value: str):
        """Set new router load balancing strategy."""
        self.router_load_balancing_strategy = value

    @rx.event
    def set_router_cost_prompt_tokens(self, value: str):
        """Set new router cost prompt tokens."""
        self.router_cost_prompt_tokens = value

    @rx.event
    def set_router_cost_completion_tokens(self, value: str):
        """Set new router cost completion tokens."""
        self.router_cost_completion_tokens = value

    ############################################################
    # edit entity
    ############################################################

    @rx.event
    def set_entity_to_edit(self, entity: Router | None):
        """Set edit entity data."""
        if entity is None:
            self.entity_to_edit = None
            self.router_name = ""
            self.router_type = ""
            self.router_aliases = ""
            self.router_load_balancing_strategy = "Shuffle"
            self.router_cost_prompt_tokens = 0.0
            self.router_cost_completion_tokens = 0.0

        else:
            self.entity_to_edit = entity.id
            self.router_name = entity.name
            self.router_type = entity.type
            self.router_aliases = ", ".join(entity.aliases) if entity.aliases else ""
            self.router_load_balancing_strategy = entity.load_balancing_strategy
            self.router_cost_prompt_tokens = entity.cost_prompt_tokens
            self.router_cost_completion_tokens = entity.cost_completion_tokens

    @rx.event
    async def update_entity(self):
        """Update a router."""
        self.update_entity_loading = True
        yield

        payload = {
            "name": self.router_name,
            "type": self.router_type,
            "aliases": self.router_aliases,
            "load_balancing_strategy": self.router_load_balancing_strategy.lower().replace(" ", "_"),
            "cost_prompt_tokens": self.router_cost_prompt_tokens,
            "cost_completion_tokens": self.router_cost_completion_tokens,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/admin/routers/{self.entity_to_edit}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
            response.raise_for_status()

        except Exception as e:
            yield rx.toast.error(f"Error updating router: {str(e)}", position="bottom-right")
        finally:
            self.update_entity_loading = False
            yield
