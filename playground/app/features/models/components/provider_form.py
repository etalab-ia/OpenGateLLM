"""Provider form component."""

import reflex as rx

from app.core.variables import (
    SIZE_MEDIUM,
    SPACING_MEDIUM,
    SPACING_SMALL,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_MEDIUM,
)
from app.features.models.state import ModelsState


def add_provider_form(router_id: int) -> rx.Component:
    """Form to add a provider to a router."""
    return rx.card(
        rx.vstack(
            rx.heading("Add provider", size=TEXT_SIZE_MEDIUM),
            rx.divider(),
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("Provider Type *", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.select(
                            ModelsState.provider_types_list,
                            placeholder="Select provider type",
                            value=ModelsState.new_provider_type,
                            on_change=ModelsState.set_new_provider_type,
                            disabled=ModelsState.add_provider_loading,
                            width="100%",
                        ),
                        spacing=SPACING_TINY,
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Model Name *", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.input(
                            placeholder="e.g., gpt-4",
                            value=ModelsState.new_provider_model_name,
                            on_change=ModelsState.set_new_provider_model_name,
                            disabled=ModelsState.add_provider_loading,
                            width="100%",
                        ),
                        spacing=SPACING_TINY,
                        width="100%",
                    ),
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                rx.hstack(
                    rx.vstack(
                        rx.text("URL", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.input(
                            placeholder="Optional (auto-filled for OpenAI/Albert)",
                            value=ModelsState.new_provider_url,
                            on_change=ModelsState.set_new_provider_url,
                            disabled=ModelsState.add_provider_loading,
                            width="100%",
                        ),
                        spacing=SPACING_TINY,
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("API Key", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.input(
                            placeholder="Optional",
                            type="password",
                            value=ModelsState.new_provider_key,
                            on_change=ModelsState.set_new_provider_key,
                            disabled=ModelsState.add_provider_loading,
                            width="100%",
                        ),
                        spacing=SPACING_TINY,
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Timeout (seconds)", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.input(
                            placeholder="300",
                            type="number",
                            value=ModelsState.new_provider_timeout.to(str),
                            on_change=ModelsState.set_new_provider_timeout,
                            disabled=ModelsState.add_provider_loading,
                            width="100%",
                        ),
                        spacing=SPACING_TINY,
                        width="100%",
                    ),
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                spacing=SPACING_SMALL,
                width="100%",
            ),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(
                        ModelsState.add_provider_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Add Provider",
                    ),
                    on_click=lambda: ModelsState.add_provider(router_id),
                    disabled=ModelsState.add_provider_loading,
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        variant="surface",
        width="100%",
    )

