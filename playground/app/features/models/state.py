"""Models management state."""

import datetime

import httpx
import reflex as rx

from app.features.chat.state import ChatState
from app.features.models.models import FormattedRouter, Provider, Router


class ModelsState(ChatState):
    """State for models (routers) management."""

    # Routers list
    routers: list[Router] = []
    routers_loading: bool = False

    # Providers for each router
    router_providers: dict[int, list[Provider]] = {}
    providers_loading: dict[int, bool] = {}

    @rx.var
    def router_has_providers_loaded(self) -> dict[int, bool]:
        """Get dict of router IDs that have providers loaded."""
        return {router_id: router_id in self.router_providers for router_id in [r.id for r in self.routers]}

    @rx.var
    def all_providers_by_router(self) -> dict[int, list[Provider]]:
        """Get all providers grouped by router ID."""
        return self.router_providers

    @rx.var
    def providers_list_by_router(self) -> dict[int, list[Provider]]:
        """Get providers list for each router (for use in components)."""
        result = {}
        for router in self.routers:
            result[router.id] = self.router_providers.get(router.id, [])
        return result

    def get_providers_for_router(self, router_id: int) -> list[Provider]:
        """Get providers list for a specific router ID."""
        return self.router_providers.get(router_id, [])

    def _get_providers_loading(self, router_id: int) -> bool:
        """Get loading state for a router's providers."""
        return self.providers_loading.get(router_id, False)

    # Add provider form
    new_provider_router_id: int | None = None
    new_provider_type: str = ""
    new_provider_url: str = ""
    new_provider_key: str = ""
    new_provider_timeout: int = 300
    new_provider_model_name: str = ""
    new_provider_carbon_zone: str = "WOR"
    new_provider_carbon_total_params: int | None = None
    new_provider_carbon_active_params: int | None = None
    new_provider_qos_metric: str | None = None
    new_provider_qos_limit: float | None = None
    add_provider_loading: bool = False

    # Delete provider
    provider_to_delete: int | None = None
    delete_provider_loading: bool = False

    # Add router form
    new_router_name: str = ""
    new_router_type: str = ""
    new_router_aliases: str = ""
    new_router_load_balancing_strategy: str = "shuffle"
    new_router_cost_prompt_tokens: float = 0.0
    new_router_cost_completion_tokens: float = 0.0
    add_router_loading: bool = False

    @rx.var
    def routers_with_formatted_dates(self) -> list[FormattedRouter]:
        """Get routers with formatted dates."""
        formatted = []
        for router in self.routers:
            formatted.append(
                FormattedRouter(
                    id=router.id,
                    name=router.name,
                    user_id=router.user_id,
                    type=router.type,
                    aliases=router.aliases,
                    load_balancing_strategy=router.load_balancing_strategy,
                    vector_size=router.vector_size,
                    max_context_length=router.max_context_length,
                    cost_prompt_tokens=router.cost_prompt_tokens,
                    cost_completion_tokens=router.cost_completion_tokens,
                    providers=router.providers,
                    created=datetime.datetime.fromtimestamp(router.created).strftime("%Y-%m-%d %H:%M"),
                    updated=datetime.datetime.fromtimestamp(router.updated).strftime("%Y-%m-%d %H:%M"),
                )
            )
        return formatted

    def get_providers_list_for_router(self, router_id: int) -> list[Provider]:
        """Get providers list for a specific router ID (for use in components)."""
        return self.router_providers.get(router_id, [])

    @rx.var
    def is_delete_provider_dialog_open(self) -> bool:
        """Check if delete provider dialog should be open."""
        return self.provider_to_delete is not None

    @rx.var
    def provider_types_list(self) -> list[str]:
        """Get list of provider types."""
        return ["albert", "openai", "tei", "vllm"]

    @rx.var
    def router_types_list(self) -> list[str]:
        """Get list of router types."""
        return [
            "image-text-to-text",
            "automatic-speech-recognition",
            "text-embeddings-inference",
            "text-generation",
            "text-classification",
        ]

    @rx.var
    def load_balancing_strategies_list(self) -> list[str]:
        """Get list of load balancing strategies."""
        return ["shuffle", "least_busy"]

    # Event handlers

    @rx.event
    def set_new_provider_router_id(self, router_id: int | None):
        """Set router ID for new provider."""
        self.new_provider_router_id = router_id

    @rx.event
    def set_new_provider_type(self, value: str):
        """Set new provider type."""
        self.new_provider_type = value

    @rx.event
    def set_new_provider_url(self, value: str):
        """Set new provider URL."""
        self.new_provider_url = value

    @rx.event
    def set_new_provider_key(self, value: str):
        """Set new provider key."""
        self.new_provider_key = value

    @rx.event
    def set_new_provider_timeout(self, value: str):
        """Set new provider timeout."""
        try:
            self.new_provider_timeout = int(value) if value.strip() else 300
        except ValueError:
            self.new_provider_timeout = 300

    @rx.event
    def set_new_provider_model_name(self, value: str):
        """Set new provider model name."""
        self.new_provider_model_name = value

    @rx.event
    def set_new_provider_carbon_zone(self, value: str):
        """Set new provider carbon zone."""
        self.new_provider_carbon_zone = value

    @rx.event
    def set_new_provider_carbon_total_params(self, value: str):
        """Set new provider carbon total params."""
        try:
            self.new_provider_carbon_total_params = int(value) if value.strip() else None
        except ValueError:
            self.new_provider_carbon_total_params = None

    @rx.event
    def set_new_provider_carbon_active_params(self, value: str):
        """Set new provider carbon active params."""
        try:
            self.new_provider_carbon_active_params = int(value) if value.strip() else None
        except ValueError:
            self.new_provider_carbon_active_params = None

    @rx.event
    def set_new_provider_qos_metric(self, value: str):
        """Set new provider QoS metric."""
        self.new_provider_qos_metric = value if value.strip() else None

    @rx.event
    def set_new_provider_qos_limit(self, value: str):
        """Set new provider QoS limit."""
        try:
            self.new_provider_qos_limit = float(value) if value.strip() else None
        except ValueError:
            self.new_provider_qos_limit = None

    @rx.event
    def set_provider_to_delete(self, provider_id: int | None):
        """Set provider to delete."""
        self.provider_to_delete = provider_id

    @rx.event
    def set_new_router_name(self, value: str):
        """Set new router name."""
        self.new_router_name = value

    @rx.event
    def set_new_router_type(self, value: str):
        """Set new router type."""
        self.new_router_type = value

    @rx.event
    def set_new_router_aliases(self, value: str):
        """Set new router aliases."""
        self.new_router_aliases = value

    @rx.event
    def set_new_router_load_balancing_strategy(self, value: str):
        """Set new router load balancing strategy."""
        self.new_router_load_balancing_strategy = value

    @rx.event
    def set_new_router_cost_prompt_tokens(self, value: str):
        """Set new router cost prompt tokens."""
        try:
            self.new_router_cost_prompt_tokens = float(value) if value.strip() else 0.0
        except ValueError:
            self.new_router_cost_prompt_tokens = 0.0

    @rx.event
    def set_new_router_cost_completion_tokens(self, value: str):
        """Set new router cost completion tokens."""
        try:
            self.new_router_cost_completion_tokens = float(value) if value.strip() else 0.0
        except ValueError:
            self.new_router_cost_completion_tokens = 0.0

    @rx.event
    async def load_routers(self):
        """Load routers from API."""
        if not self.is_authenticated or not self.api_key:
            return

        self.routers_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/routers",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code != 200:
                    error_detail = response.json().get("detail", "Failed to load routers")
                    yield rx.toast.error(str(error_detail), position="bottom-right")
                else:
                    data = response.json()
                    routers_data = data.get("data", [])
                    self.routers = [
                        Router(
                            id=r["id"],
                            name=r["name"],
                            user_id=r["user_id"],
                            type=r["type"],
                            aliases=r.get("aliases"),
                            load_balancing_strategy=r["load_balancing_strategy"],
                            vector_size=r.get("vector_size"),
                            max_context_length=r.get("max_context_length"),
                            cost_prompt_tokens=r["cost_prompt_tokens"],
                            cost_completion_tokens=r["cost_completion_tokens"],
                            providers=r.get("providers", 0),
                            created=r["created"],
                            updated=r["updated"],
                        )
                        for r in routers_data
                    ]

        except Exception as e:
            yield rx.toast.error(f"Error loading routers: {str(e)}", position="bottom-right")
        finally:
            self.routers_loading = False
            yield

    @rx.event
    async def load_providers(self, router_id: int):
        """Load providers for a specific router."""
        if not self.is_authenticated or not self.api_key:
            return

        self.providers_loading[router_id] = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/providers",
                    params={"router": router_id},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    providers_data = data.get("data", [])
                    self.router_providers[router_id] = [
                        Provider(
                            id=p["id"],
                            router_id=p["router_id"],
                            user_id=p["user_id"],
                            type=p["type"],
                            url=p["url"],
                            key=p.get("key"),
                            timeout=p["timeout"],
                            model_name=p["model_name"],
                            model_carbon_footprint_zone=p.get("model_carbon_footprint_zone"),
                            model_carbon_footprint_total_params=p.get("model_carbon_footprint_total_params"),
                            model_carbon_footprint_active_params=p.get("model_carbon_footprint_active_params"),
                            qos_metric=p.get("qos_metric"),
                            qos_limit=p.get("qos_limit"),
                            created=p.get("created"),
                            updated=p.get("updated"),
                        )
                        for p in providers_data
                    ]
                else:
                    error_detail = response.json().get("detail", "Failed to load providers")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error loading providers: {str(e)}", position="bottom-right")
        finally:
            self.providers_loading[router_id] = False
            yield

    @rx.event
    async def add_provider(self, router_id: int):
        """Add a provider to a router."""
        if not self.new_provider_model_name.strip():
            yield rx.toast.warning("Model name is required", position="bottom-right")
            return

        if not self.new_provider_type:
            yield rx.toast.warning("Provider type is required", position="bottom-right")
            return

        self.add_provider_loading = True
        yield

        try:
            payload = {
                "router": router_id,
                "type": self.new_provider_type,
                "model_name": self.new_provider_model_name.strip(),
                "timeout": self.new_provider_timeout,
            }

            if self.new_provider_url.strip():
                payload["url"] = self.new_provider_url.strip()

            if self.new_provider_key.strip():
                payload["key"] = self.new_provider_key.strip()

            if self.new_provider_carbon_zone:
                payload["model_carbon_footprint_zone"] = self.new_provider_carbon_zone

            if self.new_provider_carbon_total_params is not None:
                payload["model_carbon_footprint_total_params"] = self.new_provider_carbon_total_params

            if self.new_provider_carbon_active_params is not None:
                payload["model_carbon_footprint_active_params"] = self.new_provider_carbon_active_params

            if self.new_provider_qos_metric:
                payload["qos_metric"] = self.new_provider_qos_metric

            if self.new_provider_qos_limit is not None:
                payload["qos_limit"] = self.new_provider_qos_limit

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.opengatellm_url}/v1/admin/providers",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=60.0,
                )

                if response.status_code == 201:
                    # Clear form
                    self.new_provider_router_id = None
                    self.new_provider_type = ""
                    self.new_provider_url = ""
                    self.new_provider_key = ""
                    self.new_provider_timeout = 300
                    self.new_provider_model_name = ""
                    self.new_provider_carbon_zone = "WOR"
                    self.new_provider_carbon_total_params = None
                    self.new_provider_carbon_active_params = None
                    self.new_provider_qos_metric = None
                    self.new_provider_qos_limit = None
                    yield rx.toast.success("Provider added successfully", position="bottom-right")
                    # Reload providers and routers
                    async for _ in self.load_providers(router_id):
                        yield
                    async for _ in self.load_routers():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to add provider")
                    if isinstance(error_detail, list) and len(error_detail) > 0:
                        first_error = error_detail[0]
                        if isinstance(first_error, dict):
                            yield rx.toast.error(first_error.get("msg", str(error_detail)), position="bottom-right")
                        else:
                            yield rx.toast.error(str(first_error), position="bottom-right")
                    else:
                        yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.add_provider_loading = False
            yield

    @rx.event
    async def delete_provider(self, provider_id: int):
        """Delete a provider."""
        self.delete_provider_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.opengatellm_url}/v1/admin/providers/{provider_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 204:
                    self.provider_to_delete = None
                    yield rx.toast.success("Provider deleted successfully", position="bottom-right")
                    # Reload routers to update provider count
                    async for _ in self.load_routers():
                        yield
                    # Reload providers for affected router
                    for router in self.routers:
                        if provider_id in [p.id for p in self.router_providers.get(router.id, [])]:
                            async for _ in self.load_providers(router.id):
                                yield
                            break
                else:
                    error_detail = response.json().get("detail", "Failed to delete provider")
                    yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.delete_provider_loading = False
            yield

    @rx.event
    async def add_router(self):
        """Add a new router."""
        if not self.new_router_name.strip():
            yield rx.toast.warning("Router name is required", position="bottom-right")
            return

        if not self.new_router_type:
            yield rx.toast.warning("Router type is required", position="bottom-right")
            return

        self.add_router_loading = True
        yield

        try:
            payload = {
                "name": self.new_router_name.strip(),
                "type": self.new_router_type,
                "load_balancing_strategy": self.new_router_load_balancing_strategy,
                "cost_prompt_tokens": self.new_router_cost_prompt_tokens,
                "cost_completion_tokens": self.new_router_cost_completion_tokens,
            }

            # Parse aliases from comma-separated string
            if self.new_router_aliases.strip():
                aliases = [alias.strip() for alias in self.new_router_aliases.split(",") if alias.strip()]
                if aliases:
                    payload["aliases"] = aliases

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.opengatellm_url}/v1/admin/routers",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 201:
                    # Reset form
                    self.new_router_name = ""
                    self.new_router_type = ""
                    self.new_router_aliases = ""
                    self.new_router_load_balancing_strategy = "shuffle"
                    self.new_router_cost_prompt_tokens = 0.0
                    self.new_router_cost_completion_tokens = 0.0
                    yield rx.toast.success("Router added successfully", position="bottom-right")
                    # Reload routers
                    async for _ in self.load_routers():
                        yield
                else:
                    error_detail = response.json().get("detail", "Failed to add router")
                    if isinstance(error_detail, list) and len(error_detail) > 0:
                        first_error = error_detail[0]
                        if isinstance(first_error, dict):
                            yield rx.toast.error(first_error.get("msg", str(error_detail)), position="bottom-right")
                        else:
                            yield rx.toast.error(str(first_error), position="bottom-right")
                    else:
                        yield rx.toast.error(str(error_detail), position="bottom-right")

        except Exception as e:
            yield rx.toast.error(f"Error: {str(e)}", position="bottom-right")
        finally:
            self.add_router_loading = False
            yield
