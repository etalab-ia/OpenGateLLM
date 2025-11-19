"""Usage state for fetching account usage with pagination and filters."""

import datetime as dt
from typing import Any

import httpx
from pydantic import BaseModel
import reflex as rx

from app.features.auth.state import AuthState

_usage_endpoints = {
    "All": None,
    "Chat completions": "/v1/chat/completions",
    "Embeddings": "/v1/embeddings",
    "OCR": "/v1/ocr",
    "Rerank": "/v1/rerank",
    "Search": "/v1/search",
}


class UsageItem(BaseModel):
    created: int
    endpoint: str | None
    model: str | None
    key: str | None
    method: str | None
    status: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost: float | None
    latency: int | None
    ttft: int | None
    kwh_min: float | None
    kwh_max: float | None
    kgco2eq_min: float | None
    kgco2eq_max: float | None


class UsageState(AuthState):
    """State for account usage listing and filters."""

    # Filters
    date_from: str = (dt.datetime.now() - dt.timedelta(days=30)).strftime("%Y-%m-%d")
    date_to: str = (dt.datetime.now() + dt.timedelta(days=1)).strftime("%Y-%m-%d")
    endpoint: str = "All"

    # Pagination
    page: int = 1
    per_page: int = 20
    has_more: bool = False

    # Data
    usage: list[UsageItem] = []
    loading: bool = False

    @rx.var
    def endpoint_display_values(self) -> list[str]:
        return list(_usage_endpoints.keys())

    @rx.var
    def max_date(self) -> str:
        return (dt.datetime.now()).strftime("%Y-%m-%d")

    @rx.var
    def date_from_value(self) -> str:
        return self.date_from

    @rx.var
    def date_to_value(self) -> str:
        return self.date_to or ""

    @rx.event
    def set_date_from(self, value: str):
        self.date_from = value

    @rx.event
    def set_date_to(self, value: str):
        self.date_to = value

    @rx.event
    def set_page(self, page: int):
        self.page = page

    @rx.event
    def set_endpoint(self, value: str):
        """Set the endpoint filter using the display key."""
        self.endpoint = value

    @rx.var
    def usage_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in self.usage:
            rows.append({
                "date": dt.datetime.fromtimestamp(row.created).strftime("%Y-%m-%d %H:%M"),
                "endpoint": row.endpoint,
                "model": row.model,
                "tokens": "" if row.total_tokens == 0 else f"{row.prompt_tokens} → {row.completion_tokens}",
                "cost": "" if row.cost == 0.0 else f"{row.cost:.4f}",
                "kgCO2eq": "" if row.kgco2eq_min is None or row.kgco2eq_max is None else f"{round(row.kgco2eq_min, 5)} — {round(row.kgco2eq_max, 5)}",
            })
        return rows

    @rx.event
    async def load_usage(self):
        if not self.is_authenticated or not self.api_key:
            return

        self.loading = True
        yield

        try:
            params = {
                "offset": (self.page - 1) * self.per_page,
                "limit": self.per_page,
                "start_time": int(dt.datetime.strptime(self.date_from, "%Y-%m-%d").timestamp()),
                "end_time": int(dt.datetime.strptime(self.date_to, "%Y-%m-%d").timestamp()),
            }
            if self.endpoint is not None:
                endpoint_api_value = _usage_endpoints.get(self.endpoint, None)
                if endpoint_api_value is not None:
                    params["endpoint"] = endpoint_api_value
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url=f"{self.opengatellm_url}/v1/me/usage",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code != 200:
                    yield rx.toast.error(response.json().get("detail", "Failed to load usage"), position="bottom-right")
                else:
                    data = response.json()
                    items = data.get("data", [])
                    self.usage = [
                        UsageItem(
                            created=item.get("created", 0),
                            endpoint=item.get("endpoint", ""),
                            model=item.get("model", ""),
                            key=item.get("key", ""),
                            method=item.get("method", ""),
                            status=item.get("status", 0),
                            prompt_tokens=item.get("prompt_tokens", 0),
                            completion_tokens=item.get("completion_tokens", 0),
                            total_tokens=item.get("total_tokens", 0),
                            cost=item.get("usage", {}).get("cost", 0.0),
                            latency=item.get("usage", {}).get("metrics", {}).get("latency"),
                            ttft=item.get("usage", {}).get("metrics", {}).get("ttft"),
                            kwh_min=item.get("usage", {}).get("carbon", {}).get("kWh", {}).get("min", 0.0),
                            kwh_max=item.get("usage", {}).get("carbon", {}).get("kWh", {}).get("max", 0.0),
                            kgco2eq_min=item.get("usage", {}).get("carbon", {}).get("kgCO2eq", {}).get("min", 0.0),
                            kgco2eq_max=item.get("usage", {}).get("carbon", {}).get("kgCO2eq", {}).get("max", 0.0),
                        )
                        for item in items
                    ]
                    self.has_more = len(items) == self.per_page
        except Exception as e:
            yield rx.toast.error(str(e), position="bottom-right")
        finally:
            self.loading = False
            yield

    @rx.event
    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            yield
            async for _ in self.load_usage():
                yield

    @rx.event
    async def next_page(self):
        if self.has_more:
            self.page += 1
            yield
            async for _ in self.load_usage():
                yield
