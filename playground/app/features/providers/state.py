import datetime as dt

import httpx
import reflex as rx

from app.features.providers.models import Provider
from app.shared.states.entity_state import EntityState


class ProvidersState(EntityState):
    """Providers management state."""

    # Providers list
    entities: list[Provider] = []
    provider_owners: dict[int, str] = {}
    provider_routers: dict[int, str] = {}

    def _format_provider(self, provider: dict) -> Provider:
        """Format provider."""
        return Provider(
            id=provider["id"],
            router=self.provider_routers[provider["router_id"]],
            user=self.provider_owners[provider["user_id"]],
            type=provider["type"],
            url=provider["url"],
            key=provider["key"],
            timeout=provider["timeout"],
            model_name=provider["model_name"],
            model_carbon_footprint_zone=provider["model_carbon_footprint_zone"],
            model_carbon_footprint_total_params=provider["model_carbon_footprint_total_params"],
            model_carbon_footprint_active_params=provider["model_carbon_footprint_active_params"],
            qos_metric=provider["qos_metric"],
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
                                f"{self.opengatellm_url}/v1/admin/users/{provider["user_id"]}",
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

    @rx.event
    async def delete_entity(self, entity_id: int):
        """Delete a provider."""
        self.delete_entity_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url=f"{self.opengatellm_url}/v1/admin/providers/{entity_id}",
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
