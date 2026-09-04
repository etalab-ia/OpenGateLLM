"""Usage state for fetching daily usage buckets with filters."""

import datetime as dt
from typing import Any

import httpx
import reflex as rx

from app.features.usage.models import Usage
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState
from app.shared.utils.timestamps import DATE_FORMAT, date_to_timestamp, format_date, format_local_date, local_now

ALL_ENDPOINTS = "All endpoints"
ALL_MODELS = "All models"
ALL_KEYS = "All keys"
SYSTEM_KEY_NAMES = {"_system_playground_key", "_system_search_tool"}
USAGE_PAGE_LIMIT = 100


class UsageState(EntityState):
    """State for account usage buckets, filters, and charts."""

    entities: list[Usage] = []
    available_models: list[str] = [ALL_MODELS]
    available_keys: list[str] = [ALL_KEYS]
    key_ids_by_name: dict[str, int] = {}

    filter_date_from_value: str | None = None
    filter_date_to_value: str | None = None
    filter_endpoint_value: str = ALL_ENDPOINTS
    filter_model_value: str = ALL_MODELS
    filter_key_value: str = ALL_KEYS

    @rx.var
    def endpoints_name_list(self) -> list[str]:
        return [
            ALL_ENDPOINTS,
            "/v1/audio/transcriptions",
            "/v1/chat/completions",
            "/v1/embeddings",
            "/v1/ocr",
            "/v1/rerank",
            "/v1/search",
        ]

    def _format_bucket(self, bucket: dict) -> Usage:
        return Usage(
            start_time=bucket["start_time"],
            end_time=bucket["end_time"],
            date=format_date(bucket["start_time"]),
            prompt_tokens=bucket["prompt_tokens"],
            completion_tokens=bucket["completion_tokens"],
            total_tokens=bucket["total_tokens"],
            requests=bucket.get("requests", 0),
            cost=bucket["cost"],
            kwh=bucket["impacts"]["kWh"],
            kgco2eq=bucket["impacts"]["kgCO2eq"],
        )

    @rx.event
    async def load_entities(self):
        if not self.is_authenticated or not self.api_key:
            return

        self.entities_loading = True
        yield

        start_time = date_to_timestamp(self.get_filter_date_from_value)
        end_time = date_to_timestamp(self.get_filter_date_to_value)
        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = None
        try:
            async with httpx.AsyncClient() as client:
                models_response = await client.get(
                    url=f"{self.opengatellm_url}/v1/models",
                    headers=headers,
                    timeout=self.opengatellm_timeout,
                )
                models_response.raise_for_status()
                model_names = sorted(model.get("id") for model in models_response.json().get("data", []) if model.get("id"))
                self.available_models = [ALL_MODELS, *model_names]
                if self.filter_model_value not in self.available_models:
                    self.filter_model_value = ALL_MODELS

                keys_response = await client.get(
                    url=f"{self.opengatellm_url}/v1/keys",
                    params={"offset": 0, "limit": USAGE_PAGE_LIMIT},
                    headers=headers,
                    timeout=self.opengatellm_timeout,
                )
                keys_response.raise_for_status()
                key_ids_by_name: dict[str, int] = {}
                key_names: list[str] = []
                for key in keys_response.json().get("data", []):
                    if key["name"] in SYSTEM_KEY_NAMES:
                        continue
                    key_names.append(key["name"])
                    key_ids_by_name[key["name"]] = key["id"]
                self.available_keys = [ALL_KEYS, *key_names]
                self.key_ids_by_name = key_ids_by_name
                if self.filter_key_value not in self.available_keys:
                    self.filter_key_value = ALL_KEYS

                buckets: list[Usage] = []
                offset = 0
                total = None
                while total is None or len(buckets) < total:
                    params: dict[str, Any] = {
                        "offset": offset,
                        "limit": USAGE_PAGE_LIMIT,
                        "start_time": start_time,
                        "end_time": end_time,
                    }
                    if self.filter_endpoint_value != ALL_ENDPOINTS:
                        params["endpoint"] = self.filter_endpoint_value
                    if self.filter_model_value != ALL_MODELS:
                        params["models"] = self.filter_model_value
                    if self.filter_key_value != ALL_KEYS:
                        params["key_id"] = self.key_ids_by_name[self.filter_key_value]

                    response = await client.get(
                        url=f"{self.opengatellm_url}/v1/usage",
                        params=params,
                        headers=headers,
                        timeout=self.opengatellm_timeout,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    total = payload.get("total", 0)
                    page = [self._format_bucket(bucket) for bucket in payload.get("data", [])]
                    buckets.extend(page)
                    if not page:
                        break
                    offset += USAGE_PAGE_LIMIT

                self.entities = sorted(buckets, key=lambda bucket: bucket.start_time)

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.entities_loading = False
            yield

    @staticmethod
    def _chart_point(bucket: Usage) -> dict[str, Any]:
        return {
            "date": bucket.date,
            "prompt_tokens": bucket.prompt_tokens,
            "completion_tokens": bucket.completion_tokens,
            "total_tokens": bucket.total_tokens,
            "requests": getattr(bucket, "requests", 0),
            "cost": round(bucket.cost, 2),
            "kWh": round(bucket.kwh, 2),
            "kgCO2eq": round(bucket.kgco2eq or 0, 2),
        }

    @staticmethod
    def _empty_chart_point(date: str) -> dict[str, Any]:
        return {
            "date": date,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
            "cost": 0.0,
            "kWh": 0.0,
            "kgCO2eq": 0.0,
        }

    @rx.var
    def chart_data(self) -> list[dict[str, Any]]:
        by_date = {bucket.date: self._chart_point(bucket) for bucket in self.entities}
        start = dt.datetime.strptime(self.get_filter_date_from_value, DATE_FORMAT).date()
        end = dt.datetime.strptime(self.get_filter_date_to_value, DATE_FORMAT).date()
        points: list[dict[str, Any]] = []
        day = start
        while day < end:
            key = day.strftime(DATE_FORMAT)
            points.append(by_date.get(key) or self._empty_chart_point(key))
            day += dt.timedelta(days=1)
        return points

    @rx.var
    def summary_requests(self) -> str:
        return f"{sum(getattr(bucket, 'requests', 0) for bucket in self.entities):,}"

    @rx.var
    def summary_prompt_tokens(self) -> str:
        return f"{sum(bucket.prompt_tokens for bucket in self.entities):,}"

    @rx.var
    def summary_completion_tokens(self) -> str:
        return f"{sum(bucket.completion_tokens for bucket in self.entities):,}"

    @rx.var
    def summary_total_tokens(self) -> str:
        return f"{sum(bucket.total_tokens for bucket in self.entities):,}"

    @rx.var
    def summary_cost(self) -> str:
        return f"{sum(bucket.cost for bucket in self.entities):.2f}"

    @rx.var
    def summary_kwh(self) -> str:
        return f"{sum(bucket.kwh for bucket in self.entities):.2f}"

    @rx.var
    def summary_kgco2eq(self) -> str:
        return f"{sum(bucket.kgco2eq or 0 for bucket in self.entities):.2f}"

    @rx.var
    def get_filter_date_from_value(self) -> str:
        if self.filter_date_from_value is None:
            return format_local_date(local_now() - dt.timedelta(days=7))
        return self.filter_date_from_value

    @rx.var
    def get_filter_date_to_value(self) -> str:
        if self.filter_date_to_value is None:
            return format_local_date(local_now() + dt.timedelta(days=1))
        return self.filter_date_to_value

    @rx.var
    def filter_date_to_value_max(self) -> str:
        return format_local_date(local_now() + dt.timedelta(days=1))

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
    def set_filter_model(self, value: str):
        self.filter_model_value = value

    @rx.event
    def set_filter_key(self, value: str):
        self.filter_key_value = value

    @rx.event
    async def apply_filters(self):
        yield
        async for _ in self.load_entities():
            yield
