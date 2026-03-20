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
    def model_hosting_zones_list(self) -> list[str]:
        return sorted([country.alpha_3 for country in pycountry.countries] + ["WOR"])

    @rx.var
    def provider_qos_metric_list(self) -> list[str]:
        return sorted(["TTFT", "Latency", "Inflight", "Performance"])

    @rx.var
    def routers_name_list(self) -> list[str]:
        return sorted([router["name"] for router in self.routers_list])

    @rx.var
    def routers_name_list_with_all(self) -> list[str]:
        return ["All routers"] + sorted([router["name"] for router in self.routers_list])

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
            model_hosting_zone=provider["model_hosting_zone"],
            model_total_params=provider["model_total_params"],
            model_active_params=provider["model_active_params"],
            qos_metric=_qos_metric_converter.get(provider["qos_metric"]),
            qos_limit=provider["qos_limit"],
            created=dt.datetime.fromtimestamp(provider["created"]).strftime("%Y-%m-%d %H:%M"),
        )

    @rx.var
    def providers(self) -> list[Provider]:
        """Get providers list with correct typing for Reflex."""
        return self.entities

    @rx.event(background=True)
    async def load_entities(self):
        """Load entities."""
        async with self:
            if not self.is_authenticated or not self.api_key:
                return
            self.entities_loading = True
            url = self.opengatellm_url
            api_key = self.api_key
            page = self.page
            per_page = self.per_page
            order_by = self.order_by_value
            order_direction = self.order_direction_value
            filter_router = self.filter_router_value
            local_routers_list = list(self.routers_list)
            local_routers_dict = dict(self.routers_dict)
            local_provider_owners = dict(self.provider_owners)
            yield

        params = {
            "offset": (page - 1) * per_page,
            "limit": per_page,
            "order_by": order_by,
            "order_direction": order_direction,
        }

        response = None
        raw_providers = []
        try:
            async with httpx.AsyncClient() as client:
                if not local_routers_list:
                    offset = 0
                    local_routers_list = []
                    local_routers_dict = {}
                    while True:
                        response = await client.get(
                            url=f"{url}/v1/admin/routers",
                            params={"offset": offset, "limit": 100},
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=configuration.settings.playground_opengatellm_timeout,
                        )
                        response.raise_for_status()
                        data = response.json()
                        routers_data = data.get("data", [])
                        local_routers_list.extend([{"id": r["id"], "name": r["name"]} for r in routers_data])
                        local_routers_dict.update({r["name"]: r["id"] for r in routers_data})
                        offset += 100
                        if len(routers_data) < 100:
                            break

                if filter_router != "All routers" and filter_router in local_routers_dict:
                    params["router"] = local_routers_dict[filter_router]

                response = await client.get(
                    f"{url}/v1/admin/providers",
                    params=params,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()
                data = response.json()
                raw_providers = data.get("data", [])

                for provider in raw_providers:
                    if provider["user_id"] not in local_provider_owners:
                        response = await client.get(
                            url=f"{url}/v1/admin/users/{provider['user_id']}",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=configuration.settings.playground_opengatellm_timeout,
                        )
                        if response.status_code == 404:
                            local_provider_owners[provider["user_id"]] = "Master"
                        elif response.status_code == 200:
                            data = response.json()
                            local_provider_owners[provider["user_id"]] = data.get("email", "Unknown")
                        else:
                            local_provider_owners[provider["user_id"]] = "Unknown"

                    if provider["router_id"] not in local_routers_dict.values():
                        response = await client.get(
                            url=f"{url}/v1/admin/routers/{provider['router_id']}",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=configuration.settings.playground_opengatellm_timeout,
                        )
                        if response.status_code == 200:
                            data = response.json()
                            local_routers_dict[data["name"]] = provider["router_id"]
                        else:
                            local_routers_dict["Unknown"] = provider["router_id"]

                local_routers_list = [{"id": router_id, "name": router_name} for router_name, router_id in local_routers_dict.items()]

            async with self:
                self.routers_list = local_routers_list
                self.routers_dict = local_routers_dict
                self.provider_owners = local_provider_owners
                entities = [self._format_provider(provider) for provider in raw_providers]
                self.entities = entities
                self.has_more_page = len(entities) == per_page
                yield
        except Exception as e:
            async with self:
                yield httpx_error_toast(exception=e, response=response)
        finally:
            async with self:
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
                yield type(self).load_entities()

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
            "router_id": router_id,
            "model_name": self.entity_to_create.model_name,
            "type": self.entity_to_create.type.lower(),
            "url": self.entity_to_create.url if self.entity_to_create.url else None,
            "key": self.entity_to_create.key,
            "timeout": self.entity_to_create.timeout,
            "model_hosting_zone": self.entity_to_create.model_hosting_zone,
            "model_total_params": self.entity_to_create.model_total_params,
            "model_active_params": self.entity_to_create.model_active_params,
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
                yield type(self).load_entities()

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
            "model_hosting_zone": self.entity.model_hosting_zone,
            "model_total_params": self.entity.model_total_params,
            "model_active_params": self.entity.model_active_params,
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

            yield type(self).load_entities()

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.edit_entity_loading = False
            yield

    ############################################################
    # Pagination & filters
    ############################################################
    page: int = 1
    per_page: int = 20
    order_by_value: str = "id"
    order_direction: str = "asc"
    order_direction_options: list[str] = ["asc", "desc"]
    order_direction_value: str = "asc"
    order_by_options: list[str] = ["id", "model_name", "created"]

    @rx.event(background=True)
    async def set_order_by(self, value: str):
        """Set order by field and reload."""
        async with self:
            self.order_by_value = value
            self.page = 1
            self.has_more_page = False
            yield type(self).load_entities()

    @rx.event(background=True)
    async def set_order_direction(self, value: str):
        """Set order direction and reload."""
        async with self:
            self.order_direction_value = value
            self.page = 1
            self.has_more_page = False
            yield type(self).load_entities()

    @rx.event(background=True)
    async def prev_page(self):
        async with self:
            if self.page > 1:
                self.page -= 1
                yield type(self).load_entities()

    @rx.event(background=True)
    async def next_page(self):
        async with self:
            if self.has_more_page:
                self.page += 1
                yield type(self).load_entities()

    filter_router_value: str = "All routers"

    @rx.event(background=True)
    async def set_filter_router(self, value: str):
        async with self:
            self.filter_router_value = value
            self.page = 1
            self.has_more_page = False
            yield type(self).load_entities()
