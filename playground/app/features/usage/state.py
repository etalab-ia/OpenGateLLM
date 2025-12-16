"""Usage state for fetching account usage with pagination and filters."""

import datetime as dt
from typing import Any

import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.usage.models import Usage
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState


class UsageState(EntityState):
    """State for account usage listing and filters."""

    @rx.var
    def endpoints_name_list(self) -> list[str]:
        return ["All endpoints", "/v1/chat/completions", "/v1/embeddings", "/v1/ocr", "/v1/rerank", "/v1/search"]

    ############################################################
    # Load entities
    ############################################################
    entities: list[Usage] = []

    def _format_usage(self, usage: dict) -> Usage:
        return Usage(
            created=dt.datetime.fromtimestamp(usage["created"]).strftime("%Y-%m-%d %H:%M"),
            endpoint=usage["endpoint"],
            model=usage["model"],
            key=usage["key"],
            prompt_tokens=usage["usage"]["prompt_tokens"],
            completion_tokens=usage["usage"]["completion_tokens"],
            total_tokens=usage["usage"]["total_tokens"],
            cost=usage["usage"]["cost"],
            kgco2eq_min=usage["usage"]["carbon"]["kgCO2eq"]["min"],
            kgco2eq_max=usage["usage"]["carbon"]["kgCO2eq"]["max"],
        )

    @rx.event
    async def load_entities(self):
        if not self.is_authenticated or not self.api_key:
            return

        self.entities_loading = True
        yield

        start_time = int(dt.datetime.strptime(self.get_filter_date_from_value, "%Y-%m-%d").timestamp())
        end_time = int(dt.datetime.strptime(self.get_filter_date_to_value, "%Y-%m-%d").timestamp())

        params = {
            "offset": (self.page - 1) * self.per_page,
            "limit": self.per_page,
            "start_time": start_time,
            "end_time": end_time,
        }
        if self.filter_endpoint_value != "All endpoints":
            params["endpoint"] = self.filter_endpoint_value

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url=f"{self.opengatellm_url}/v1/me/usage",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()
                data = response.json()
                self.entities = [self._format_usage(usage) for usage in data.get("data", [])]

            self.has_more_page = len(self.entities) == self.per_page

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.entities_loading = False
            yield

    @rx.var
    def usage_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in self.entities:
            rows.append({
                "date": row.created,
                "endpoint": row.endpoint,
                "key": row.key,
                "model": row.model,
                "tokens": "" if row.total_tokens == 0 else f"{row.prompt_tokens} → {row.completion_tokens}",
                "cost": "" if row.cost == 0.0 or row.cost is None else f"{row.cost:.4f}",
                "kgCO2eq": "" if row.kgco2eq_min is None or row.kgco2eq_max is None else f"{round(row.kgco2eq_min, 5)} — {round(row.kgco2eq_max, 5)}",
            })
        return rows

    ############################################################
    # Pagination & filters
    ############################################################
    per_page: int = 20

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

    filter_date_from_value: str | None = None
    filter_date_to_value: str | None = None
    filter_endpoint_value: str = "All endpoints"

    @rx.var
    def get_filter_date_from_value(self) -> str:
        if self.filter_date_from_value is None:
            return (dt.datetime.now() - dt.timedelta(days=30)).strftime("%Y-%m-%d")
        return self.filter_date_from_value

    @rx.var
    def get_filter_date_to_value(self) -> str:
        if self.filter_date_to_value is None:
            return (dt.datetime.now() + dt.timedelta(days=1)).strftime("%Y-%m-%d")
        return self.filter_date_to_value

    @rx.var
    def filter_date_to_value_max(self) -> str:
        return (dt.datetime.now() + dt.timedelta(days=1)).strftime("%Y-%m-%d")

    @rx.event
    def set_filter_date_from(self, value: str):
        self.filter_date_from_value = value

    @rx.event
    def set_filter_date_to(self, value: str):
        self.filter_date_to_value = value

    @rx.event
    def set_filter_endpoint(self, value: str):
        self.filter_endpoint_value = value

    @rx.event
    async def apply_filters(self):
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_entities():
            yield
