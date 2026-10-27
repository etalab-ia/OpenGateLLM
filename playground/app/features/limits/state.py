"""Limits state for the consumption of each allowed model's rate limits."""

import httpx
import reflex as rx

from app.features.limits.models import Limit, ModelLimits
from app.shared.components.toasts import httpx_error_toast
from app.shared.states.entity_state import EntityState

LIMIT_TYPE_LABELS = {
    "rpm": "Requests per minute",
    "rpd": "Requests per day",
    "tpm": "Tokens per minute",
    "tpd": "Tokens per day",
}


class LimitsState(EntityState):
    """State for the rate limits of the models the user is allowed to use."""

    entities: list[ModelLimits] = []

    @staticmethod
    def _format_number(number: int) -> str:
        for divisor, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
            if number >= divisor:
                return f"{number / divisor:.1f}".removesuffix(".0") + suffix
        return str(number)

    def _format_limit(self, limit: dict) -> Limit:
        type_label = LIMIT_TYPE_LABELS[limit["type"]]
        if limit["value"] is None:
            return Limit(type_label=type_label, is_unlimited=True)

        used = max(0, limit["value"] - limit["remaining"])
        return Limit(
            type_label=type_label,
            used=self._format_number(used),
            value=self._format_number(limit["value"]),
            # A limit of 0 blocks the model: it is fully used before any request.
            percent=min(100, used * 100 // limit["value"]) if limit["value"] else 100,
        )

    @rx.event
    async def load_entities(self):
        if not self.is_authenticated or not self.api_key:
            return

        self.entities_loading = True
        yield

        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url=f"{self.opengatellm_url}/v1/limits",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=self.opengatellm_timeout,
                )
                response.raise_for_status()
                self.entities = [
                    ModelLimits(model=model_limits["model"], limits=[self._format_limit(limit) for limit in model_limits["limits"]])
                    for model_limits in response.json()["data"]
                ]

        except Exception as e:
            yield httpx_error_toast(exception=e, response=response)
        finally:
            self.entities_loading = False
            yield
