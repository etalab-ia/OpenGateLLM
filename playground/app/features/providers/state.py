import datetime as dt

import httpx
import pycountry
import reflex as rx

from app.features.providers.models import Provider
from app.shared.states.entity_state import EntityState


class ProvidersState(EntityState):
    """Providers management state."""

    @rx.var
    def provider_types_list(self) -> list[str]:
        """Get list of provider types."""
        return ["Albert", "OpenAI", "TEI", "vLLM"]

    @rx.var
    def provider_carbon_footprint_zones_list(self) -> list[str]:
        return [country.alpha_3 for country in pycountry.countries] + ["WOR"]

    @rx.var
    def provider_qos_metric_list(self) -> list[str]:
        return ["TTFT", "Latency", "Inflight", "Performance"]

    ############################################################
    # Load entities
    ############################################################
    entities: list[Provider] = []
    provider_owners: dict[int, str] = {}
    provider_routers: dict[int, str] = {}

    def _format_provider(self, provider: dict) -> Provider:
        """Format provider."""

        _type_converter = {
            "vllm": "vLLM",
            "albert": "Albert",
            "openai": "OpenAI",
            "tei": "TEI",
        }

        _qos_metric_converter = {
            "ttft": "TTFT",
            "latency": "Latency",
            "inflight": "Inflight",
            "performance": "Performance",
        }

        return Provider(
            id=provider["id"],
            router=self.provider_routers.get(provider["router_id"], "Unknown"),
            user=self.provider_owners.get(provider["user_id"], "Unknown"),
            type=_type_converter.get(provider["type"]),
            url=provider["url"],
            key=provider["key"],
            timeout=provider["timeout"],
            model_name=provider["model_name"],
            model_carbon_footprint_zone=provider["model_carbon_footprint_zone"],
            model_carbon_footprint_total_params=provider["model_carbon_footprint_total_params"],
            model_carbon_footprint_active_params=provider["model_carbon_footprint_active_params"],
            qos_metric=_qos_metric_converter.get(provider["qos_metric"]),
            qos_limit=provider["qos_limit"],
            created=dt.datetime.fromtimestamp(provider["created"]).strftime("%Y-%m-%d %H:%M"),
        )

    @rx.var
    def providers(self) -> list[Provider]:
        """Get providers list with correct typing for Reflex."""
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
                    f"{self.opengatellm_url}/v1/admin/providers",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                response.raise_for_status()
                data = response.json()
                self.entities = []
                for provider in data.get("data", []):
                    if provider["user_id"] not in self.provider_owners:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                url=f"{self.opengatellm_url}/v1/admin/users/{provider["user_id"]}",
                                headers={"Authorization": f"Bearer {self.api_key}"},
                                timeout=60.0,
                            )
                            if response.status_code == 404:
                                self.provider_owners[provider["user_id"]] = "Master"
                            elif response.status_code == 200:
                                data = response.json()
                                self.provider_owners[provider["user_id"]] = data.get("name", "Unknown")
                            else:
                                self.provider_owners[provider["user_id"]] = "Unknown"

                    if provider["router_id"] not in self.provider_routers:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                url=f"{self.opengatellm_url}/v1/admin/routers/{provider["router_id"]}",
                                headers={"Authorization": f"Bearer {self.api_key}"},
                                timeout=60.0,
                            )

                            if response.status_code == 200:
                                data = response.json()
                                self.provider_routers[provider["router_id"]] = data.get("name", "Unknown")
                            else:
                                self.provider_routers[provider["router_id"]] = "Unknown"

                    self.entities.append(self._format_provider(provider))

        except Exception as e:
            yield rx.toast.error(f"Error loading providers: {str(e)}", position="bottom-right")
        finally:
            self.entities_loading = False
            yield

    ############################################################
    # Display info
    ############################################################

    @rx.event
    def set_entity_to_display_info(self, entity: Provider | None):
        """Set edit entity data."""
        if entity is None:
            self.info_entity.id = None
        else:
            self.info_entity = entity

    ############################################################
    # Delete entity
    ############################################################
    @rx.event
    async def delete_entity(self):
        """Delete a provider."""
        self.delete_entity_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/admin/providers/{self.delete_entity_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )
                response.raise_for_status()

                self.set_entity_to_delete(None)
                yield rx.toast.success("Provider deleted successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield rx.toast.error(f"Error deleting provider: {str(e)}", position="bottom-right")
        finally:
            self.delete_entity_loading = False
            yield

    ############################################################
    # Create entity
    ############################################################
    new_provider_router: str | None = None
    new_provider_model_name: str = ""
    new_provider_type: str = ""
    new_provider_url: str = ""
    new_provider_key: str = ""
    new_provider_timeout: int = 300
    new_provider_carbon_footprint_zone: str = "WOR"
    new_provider_carbon_footprint_total_params: int | None = None
    new_provider_carbon_footprint_active_params: int | None = None
    new_provider_qos_metric: str = "TTFT"
    new_provider_qos_limit: float | None = None

    @rx.event
    async def create_entity(self):
        """Create a provider."""
        if not self.new_provider_router:
            yield rx.toast.warning("Router is required", position="bottom-right")
            return

        if not self.new_provider_model_name:
            yield rx.toast.warning("Model name is required", position="bottom-right")
            return

        if not self.new_provider_type:
            yield rx.toast.warning("Type is required", position="bottom-right")
            return

        if not self.new_provider_url:
            yield rx.toast.warning("URL is required", position="bottom-right")
            return

        self.create_entity_loading = True
        yield

        payload = {
            "router": self.new_provider_router,
            "model_name": self.new_provider_model_name,
            "type": self.new_provider_type.lower(),
            "url": self.new_provider_url.lower(),
            "key": self.new_provider_key,
            "timeout": self.new_provider_timeout,
            "carbon_footprint_zone": self.new_provider_carbon_footprint_zone,
            "carbon_footprint_total_params": self.new_provider_carbon_footprint_total_params,
            "carbon_footprint_active_params": self.new_provider_carbon_footprint_active_params,
            "qos_metric": self.new_provider_qos_metric,
            "qos_limit": self.new_provider_qos_limit,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/admin/providers",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=60.0,
                )
                response.raise_for_status()

                yield rx.toast.success("Provider created successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield rx.toast.error(f"Error creating provider: {str(e)}", position="bottom-right")
        finally:
            self.create_entity_loading = False
            yield

    @rx.event
    def set_new_provider_router(self, value: str):
        """Set new provider router."""
        self.new_provider_router = value

    @rx.event
    def set_new_provider_model_name(self, value: str):
        """Set new provider model name."""
        self.new_provider_model_name = value.strip()

    @rx.event
    def set_new_provider_type(self, value: str):
        """Set new provider type."""
        self.new_provider_type = value

    @rx.event
    def set_new_provider_url(self, value: str):
        """Set new provider URL."""
        self.new_provider_url = value.strip().lower()

    @rx.event
    def set_new_provider_key(self, value: str):
        """Set new provider key."""
        self.new_provider_key = value.strip()

    @rx.event
    def set_new_provider_timeout(self, value: str):
        """Set new provider timeout."""
        self.new_provider_timeout = value

    @rx.event
    def set_new_provider_carbon_footprint_zone(self, value: str):
        """Set new provider carbon footprint zone."""
        self.new_provider_carbon_footprint_zone = value

    @rx.event
    def set_new_provider_carbon_footprint_total_params(self, value: str):
        """Set new provider carbon footprint total params."""
        self.new_provider_carbon_footprint_total_params = value

    @rx.event
    def set_new_provider_carbon_footprint_active_params(self, value: str):
        """Set new provider carbon footprint active params."""
        self.new_provider_carbon_footprint_active_params = value

    @rx.event
    def set_new_provider_qos_metric(self, value: str):
        """Set new provider QoS metric."""
        self.new_provider_qos_metric = value

    @rx.event
    def set_new_provider_qos_limit(self, value: str):
        """Set new provider QoS limit."""
        self.new_provider_qos_limit = value
