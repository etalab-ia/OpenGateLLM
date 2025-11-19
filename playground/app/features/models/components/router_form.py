"""Router form component."""

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


def add_router_form() -> rx.Component:
    """Form to add a router."""
    return rx.card(
        rx.vstack(
            rx.heading("Add router", size=TEXT_SIZE_MEDIUM),
            rx.divider(),
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("Router Name *", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.input(
                            placeholder="e.g., my-router",
                            value=ModelsState.new_router_name,
                            on_change=ModelsState.set_new_router_name,
                            disabled=ModelsState.add_router_loading,
                            width="100%",
                        ),
                        spacing=SPACING_TINY,
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Router Type *", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.select(
                            ModelsState.router_types_list,
                            placeholder="Select router type",
                            value=ModelsState.new_router_type,
                            on_change=ModelsState.set_new_router_type,
                            disabled=ModelsState.add_router_loading,
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
                        rx.text("Load Balancing Strategy", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.select(
                            ModelsState.load_balancing_strategies_list,
                            placeholder="Select strategy",
                            value=ModelsState.new_router_load_balancing_strategy,
                            on_change=ModelsState.set_new_router_load_balancing_strategy,
                            disabled=ModelsState.add_router_loading,
                            width="100%",
                        ),
                        spacing=SPACING_TINY,
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Aliases (comma-separated)", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.input(
                            placeholder="e.g., alias1, alias2",
                            value=ModelsState.new_router_aliases,
                            on_change=ModelsState.set_new_router_aliases,
                            disabled=ModelsState.add_router_loading,
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
                        rx.text("Cost per million prompt tokens", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.input(
                            placeholder="0.0",
                            type="number",
                            step="0.0001",
                            value=ModelsState.new_router_cost_prompt_tokens.to(str),
                            on_change=ModelsState.set_new_router_cost_prompt_tokens,
                            disabled=ModelsState.add_router_loading,
                            width="100%",
                        ),
                        spacing=SPACING_TINY,
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Cost per million completion tokens", size=TEXT_SIZE_LABEL, weight="bold"),
                        rx.input(
                            placeholder="0.0",
                            type="number",
                            step="0.0001",
                            value=ModelsState.new_router_cost_completion_tokens.to(str),
                            on_change=ModelsState.set_new_router_cost_completion_tokens,
                            disabled=ModelsState.add_router_loading,
                            width="100%",
                        ),
                        spacing=SPACING_TINY,
                        width="100%",
                    ),
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(
                        ModelsState.add_router_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Add Router",
                    ),
                    on_click=ModelsState.add_router,
                    disabled=ModelsState.add_router_loading,
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        variant="surface",
        width="100%",
    )

