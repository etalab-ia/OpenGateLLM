import datetime as dt

import httpx
import pycountry
import reflex as rx

from app.core.configuration import configuration
from app.features.providers.models import Provider
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState


class ProvidersState(EntityState):
    """Providers management state."""

    @rx.var
    def provider_types_list(self) -> list[str]:
        """Get list of provider types."""
        return sorted(["Albert", "Mistral", "OpenAI", "TEI", "vLLM"])

    @rx.var
    def provider_model_carbon_footprint_zones_list(self) -> list[str]:
        return sorted([country.alpha_3 for country in pycountry.countries] + ["WOR"])

    @rx.var
    def provider_qos_metric_list(self) -> list[str]:
        return sorted(["TTFT", "Latency", "Inflight", "Performance"])

    @rx.var
    def routers_name_list(self) -> list[str]:
        return sorted([router["name"] for router in self.routers_list])

    ############################################################
    # Load entities
    ############################################################
    entities: list[Provider] = []
    provider_owners: dict[int, str] = {}
    routers_dict: dict[str, int] = {}
    routers_list: list[dict[str, str | int]] = []

    def _format_provider(self, provider: dict) -> Provider:
        """Format provider."""

        router_dict_reverse = {v: k for k, v in self.routers_dict.items()}

        _type_converter = {
            "albert": "Albert",
            "mistral": "Mistral",
            "openai": "OpenAI",
            "tei": "TEI",
            "vllm": "vLLM",
        }

        _qos_metric_converter = {
            "ttft": "TTFT",
            "latency": "Latency",
            "inflight": "Inflight",
            "performance": "Performance",
        }

        router_name = router_dict_reverse.get(provider["router_id"], "Unknown")

        return Provider(
            id=provider["id"],
            router=router_name,
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

        params = {
            "offset": (self.page - 1) * self.per_page,
            "limit": self.per_page,
            "order_by": self.order_by_value,
            "order_direction": self.order_direction_value,
        }

        if self.filter_router_value != "0":
            params["router"] = int(self.filter_router_value)

        response = None
        try:
            async with httpx.AsyncClient() as client:
                # Load routers
                if not self.routers_list:
                    offset = 0
                    self.routers_list = []
                    self.routers_dict = {}
                    while True:
                        response = await client.get(
                            url=f"{self.opengatellm_url}/v1/admin/routers",
                            params={"offset": offset, "limit": 100},
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            timeout=configuration.settings.playground_opengatellm_timeout,
                        )

                        response.raise_for_status()
                        data = response.json()
                        routers_data = data.get("data", [])
                        self.routers_list.extend([{"id": router["id"], "name": router["name"]} for router in routers_data])
                        self.routers_dict.update({router["name"]: router["id"] for router in routers_data})
                        offset += 100
                        if len(routers_data) < 100:
                            break

                response = await client.get(
                    f"{self.opengatellm_url}/v1/admin/providers",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )

                response.raise_for_status()
                data = response.json()
                self.entities = []

                for provider in data.get("data", []):
                    if provider["user_id"] not in self.provider_owners:
                        response = await client.get(
                            url=f"{self.opengatellm_url}/v1/admin/users/{provider["user_id"]}",
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            timeout=configuration.settings.playground_opengatellm_timeout,
                        )
                        if response.status_code == 404:
                            self.provider_owners[provider["user_id"]] = "Master"
                        elif response.status_code == 200:
                            data = response.json()
                            self.provider_owners[provider["user_id"]] = data.get("email", "Unknown")
                        else:
                            self.provider_owners[provider["user_id"]] = "Unknown"

                    if provider["router_id"] not in self.routers_dict.values():
                        response = await client.get(
                            url=f"{self.opengatellm_url}/v1/admin/routers/{provider["router_id"]}",
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            timeout=configuration.settings.playground_opengatellm_timeout,
                        )

                        if response.status_code == 200:
                            data = response.json()
                            self.routers_dict[data["name"]] = provider["router_id"]
                        else:
                            self.routers_dict["Unknown"] = provider["router_id"]

                    self.routers_list = [{"id": router_id, "name": router_name} for router_name, router_id in self.routers_dict.items()]  # fmt: off

                    self.entities.append(self._format_provider(provider))

            self.has_more_page = len(self.entities) == self.per_page
        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.entities_loading = False
            yield

    ############################################################
    # Delete entity
    ############################################################
    entity_to_delete = Provider()

    @rx.event
    def set_entity_to_delete(self, entity: Provider):
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
            self.entity_to_delete = Provider()

    @rx.event
    async def delete_entity(self):
        """Delete a provider."""
        self.delete_entity_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/admin/providers/{self.entity_to_delete.id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                self.handle_delete_entity_dialog_change(is_open=False)
                yield rx.toast.success("Provider deleted successfully", position="bottom-right")
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
    entity_to_create: Provider = Provider()

    @rx.event
    def set_new_entity_attribut(self, attribute: str, value: str | bool | None):
        """Set new entity attributes."""
        if isinstance(value, str):
            setattr(self.entity_to_create, attribute, value.strip())
        else:
            setattr(self.entity_to_create, attribute, value)

    @rx.event
    async def create_entity(self):
        """Create a provider."""
        if not self.entity_to_create.router:
            yield rx.toast.warning("Router is required", position="bottom-right")
            return

        router_id = self.routers_dict.get(self.entity_to_create.router, None)
        if not router_id:
            yield rx.toast.warning("Router not found", position="bottom-right")
            return

        if not self.entity_to_create.model_name:
            yield rx.toast.warning("Model name is required", position="bottom-right")
            return

        if not self.entity_to_create.type:
            yield rx.toast.warning("Type is required", position="bottom-right")
            return

        self.create_entity_loading = True
        yield

        payload = {
            "router": router_id,
            "model_name": self.entity_to_create.model_name,
            "type": self.entity_to_create.type.lower(),
            "url": self.entity_to_create.url if self.entity_to_create.url else None,
            "key": self.entity_to_create.key,
            "timeout": self.entity_to_create.timeout,
            "model_carbon_footprint_zone": self.entity_to_create.model_carbon_footprint_zone,
            "model_carbon_footprint_total_params": self.entity_to_create.model_carbon_footprint_total_params,
            "model_carbon_footprint_active_params": self.entity_to_create.model_carbon_footprint_active_params,
            "qos_metric": self.entity_to_create.qos_metric.lower() if self.entity_to_create.qos_metric else None,
            "qos_limit": self.entity_to_create.qos_limit,
        }

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengatellm_url}/v1/admin/providers",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()

                yield rx.toast.success("Provider created successfully", position="bottom-right")
                async for _ in self.load_entities():
                    yield

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.create_entity_loading = False
            yield

    ############################################################
    # Edit entity
    ############################################################
    entity: Provider = Provider()

    @rx.event
    def set_entity_settings(self, entity: Provider):
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
            self.entity = Provider()

    @rx.event
    async def edit_entity(self):
        """Update a provider."""
        self.edit_entity_loading = True
        yield

        payload = {
            "router": self.routers_dict.get(self.entity.router, None),
            "timeout": self.entity.timeout,
            "model_carbon_footprint_zone": self.entity.model_carbon_footprint_zone,
            "model_carbon_footprint_total_params": self.entity.model_carbon_footprint_total_params,
            "model_carbon_footprint_active_params": self.entity.model_carbon_footprint_active_params,
            "qos_metric": self.entity.qos_metric.lower() if self.entity.qos_metric else None,
            "qos_limit": self.entity.qos_limit,
        }

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url=f"{self.opengatellm_url}/v1/admin/providers/{self.entity.id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
            response.raise_for_status()

            self.handle_settings_entity_dialog_change(is_open=False)
            yield rx.toast.success("Provider updated successfully", position="bottom-right")

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
    filter_router_value: str = "0"
    per_page: int = 20
    order_by_options: list[str] = ["id", "name", "created"]

    @rx.event
    async def set_filter_router(self, value: str):
        self.filter_router_value = value
        yield
        async for _ in self.load_entities():
            yield

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
