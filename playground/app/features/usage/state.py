"""Usage state for fetching account usage with pagination and filters."""

import datetime as dt
from typing import Any

import httpx
from pydantic import BaseModel
import reflex as rx

from app.features.auth.state import AuthState
from app.features.keys.models import Limit


class UsageItem(BaseModel):
    datetime: int
    endpoint: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float


class UsageState(AuthState):
    """State for account usage listing and filters."""

    # Filters
    date_from: str | None = None  # YYYY-MM-DD
    date_to: str | None = None  # YYYY-MM-DD

    # Pagination
    page: int = 1
    total_pages: int = 0
    total_count: int = 0
    has_more: bool = False

    # Data
    usage: list[UsageItem] = []
    loading: bool = False

    @rx.var
    def min_to_date(self) -> str:
        return self.date_from or ""

    @rx.var
    def max_from_date(self) -> str:
        return self.date_to or ""

    @rx.var
    def date_from_value(self) -> str:
        return self.date_from or ""

    @rx.var
    def date_to_value(self) -> str:
        return self.date_to or ""

    @rx.var
    def usage_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for u in self.usage:
            dt_str = dt.datetime.fromtimestamp(u.datetime).strftime("%Y-%m-%d %H:%M")
            rows.append({
                "datetime": dt_str,
                "endpoint": u.endpoint,
                "model": u.model,
                "tokens": f"{u.prompt_tokens} → {u.completion_tokens}",
                "cost": f"{u.cost:.4f}",
            })
        return rows

    @rx.var
    def requests_per_day(self) -> list[dict[str, Any]]:
        """Calculate number of requests per day for charting."""
        buckets: dict[str, int] = {}
        for u in self.usage:
            day = dt.datetime.fromtimestamp(u.datetime).strftime("%Y-%m-%d")
            buckets[day] = buckets.get(day, 0) + 1
        # sort by day
        result: list[dict[str, Any]] = []
        for k in sorted(buckets.keys()):
            result.append({
                "day": k,
                "count": buckets[k],
            })
        return result

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
    async def load_usage(self):
        if not self.is_authenticated or not self.api_key:
            return

        self.loading = True
        yield

        try:
            params: dict[str, Any] = {
                "page": self.page,
                "limit": 20,
                "order_by": "datetime",
                "order_direction": "desc",
            }

            if self.date_from:
                try:
                    ts_from = int(dt.datetime.strptime(self.date_from, "%Y-%m-%d").replace(tzinfo=dt.UTC).timestamp())
                    params["date_from"] = ts_from
                except Exception:
                    pass

            if self.date_to:
                try:
                    # include end of day
                    ts_to = int(dt.datetime.strptime(self.date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=dt.UTC).timestamp())
                    params["date_to"] = ts_to
                except Exception:
                    pass

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.opengatellm_url}/v1/usage",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if resp.status_code != 200:
                    yield rx.toast.error(resp.json().get("detail", "Failed to load usage"), position="bottom-right")
                else:
                    data = resp.json()
                    self.total_count = data.get("total", 0)
                    self.total_pages = data.get("total_pages", 0)
                    self.has_more = data.get("has_more", False)
                    items = data.get("data", [])
                    self.usage = [
                        UsageItem(
                            datetime=item.get("datetime", 0),
                            endpoint=item.get("endpoint", ""),
                            model=item.get("model", ""),
                            prompt_tokens=item.get("prompt_tokens", 0),
                            completion_tokens=item.get("completion_tokens", 0),
                            total_tokens=item.get("total_tokens", 0),
                            cost=item.get("cost", 0.0),
                        )
                        for item in items
                    ]
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
        if self.has_more or (self.total_pages and self.page < self.total_pages):
            self.page += 1
            yield
            async for _ in self.load_usage():
                yield

    @rx.var
    def formatted_limits(self) -> list[Limit]:
        """Get formatted limits from user data."""
        limits = []
        for limit_dict in self.user_limits:
            limits.append(
                Limit(
                    model=limit_dict.get("model", ""),
                    type=limit_dict.get("type", ""),
                    value=limit_dict.get("value"),
                )
            )
        return limits

    @rx.var
    def limits_by_model(self) -> dict[str, dict[str, int | None]]:
        """Group limits by model for table display."""
        result = {}
        for limit in self.formatted_limits:
            if limit.model not in result:
                result[limit.model] = {"rpm": None, "rpd": None, "tpm": None, "tpd": None}
            result[limit.model][limit.type.lower()] = limit.value
        return result

    @rx.var
    def models_list(self) -> list[str]:
        """Get list of models from limits."""
        return list(self.limits_by_model.keys())
