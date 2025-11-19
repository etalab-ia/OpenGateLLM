"""Models list component."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    ICON_SIZE_EMPTY_STATE,
    ICON_SIZE_MEDIUM,
    PADDING_PAGE,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_SMALL,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_LARGE,
    TEXT_SIZE_MEDIUM,
)
from app.features.models.components.provider_delete_dialog import delete_provider_dialog
from app.features.models.components.provider_form import add_provider_form
from app.features.models.components.router_form import add_router_form
from app.features.models.models import FormattedRouter, Provider
from app.features.models.state import ModelsState


def provider_row(provider: Provider) -> rx.Component:
    """Display a row with provider information."""
    return rx.table.row(
        rx.table.cell(
            rx.text(
                provider.model_name,
                size=TEXT_SIZE_LABEL,
                weight="medium",
                color=rx.color("mauve", 12),
            ),
        ),
        rx.table.cell(
            rx.text(
                provider.type.upper(),
                size=TEXT_SIZE_LABEL,
            ),
        ),
        rx.table.cell(
            rx.text(
                provider.url,
                size=TEXT_SIZE_LABEL,
                color=rx.color("mauve", 10),
            ),
        ),
        rx.table.cell(
            rx.text(
                str(provider.timeout) + "s",
                size=TEXT_SIZE_LABEL,
            ),
        ),
        rx.table.cell(
            rx.button(
                rx.icon("trash-2", size=ICON_SIZE_MEDIUM),
                on_click=lambda: ModelsState.set_provider_to_delete(provider.id),
                variant="soft",
                color_scheme="red",
                size=TEXT_SIZE_LABEL,
                disabled=ModelsState.delete_provider_loading,
            ),
            justify="end",
        ),
        align="center",
    )


def providers_table(router: FormattedRouter) -> rx.Component:
    """Display providers table for a router."""
    # Access providers directly from the computed var using router.id as key
    # Similar to roles: RolesState.roles_routers_lists[role.id]
    providers_list = ModelsState.providers_list_by_router[router.id]

    return rx.foreach(
        providers_list,
        provider_row,
    )


def router_accordion_item(router: FormattedRouter) -> rx.Component:
    """Display a single router as an accordion item."""
    return rx.accordion.item(
        header=rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            router.name,
                            size=TEXT_SIZE_LARGE,
                            weight="bold",
                            color=rx.color("mauve", 12),
                        ),
                        rx.badge(
                            router.id.to(str),
                            variant="soft",
                            color_scheme="blue",
                        ),
                        rx.badge(
                            router.type.replace("-", " ").title(),
                            variant="soft",
                            color_scheme="purple",
                        ),
                        rx.badge(
                            router.providers.to(str) + " provider" + rx.cond(router.providers != 1, "s", ""),
                            variant="soft",
                            color_scheme="green",
                        ),
                        spacing=SPACING_SMALL,
                    ),
                    rx.hstack(
                        rx.text(
                            f"Created: {router.created}",
                            size=TEXT_SIZE_LABEL,
                            color=rx.color("mauve", 9),
                        ),
                        rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                        rx.text(
                            f"Updated: {router.updated}",
                            size=TEXT_SIZE_LABEL,
                            color=rx.color("mauve", 9),
                        ),
                        spacing=SPACING_SMALL,
                    ),
                    rx.cond(
                        router.aliases,
                        rx.hstack(
                            rx.text("Aliases:", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 10)),
                            rx.foreach(
                                router.aliases,
                                lambda alias: rx.badge(
                                    alias,
                                    variant="outline",
                                    color_scheme="gray",
                                ),
                            ),
                            spacing=SPACING_SMALL,
                            wrap="wrap",
                        ),
                    ),
                    spacing=SPACING_SMALL,
                    align_items="start",
                    flex="1",
                ),
                width="100%",
                align="center",
                justify="between",
            ),
            rx.divider(),
            spacing=SPACING_SMALL,
            width="100%",
        ),
        content=rx.vstack(
            rx.vstack(
                rx.heading("Providers", size=TEXT_SIZE_MEDIUM),
                rx.cond(
                    ModelsState.providers_loading.get(router.id, False),
                    rx.center(
                        rx.spinner(size=SIZE_MEDIUM),
                        width="100%",
                        padding="1em",
                    ),
                    rx.cond(
                        ModelsState.router_has_providers_loaded.get(router.id, False),
                        rx.cond(
                            ModelsState.providers_list_by_router[router.id].length() > 0,
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("Model Name"),
                                        rx.table.column_header_cell("Type"),
                                        rx.table.column_header_cell("URL"),
                                        rx.table.column_header_cell("Timeout"),
                                        rx.table.column_header_cell(justify="end"),
                                    ),
                                ),
                                rx.table.body(
                                    providers_table(router),
                                ),
                                variant="surface",
                                width="100%",
                            ),
                            rx.center(
                                rx.text(
                                    "No providers yet",
                                    size=TEXT_SIZE_LABEL,
                                    color=rx.color("mauve", 9),
                                ),
                                width="100%",
                                padding="1em",
                            ),
                        ),
                        rx.center(
                            rx.button(
                                rx.icon("refresh-cw", size=ICON_SIZE_MEDIUM),
                                "Load Providers",
                                on_click=lambda: ModelsState.load_providers(router.id),
                                variant="soft",
                            ),
                            width="100%",
                            padding="1em",
                        ),
                    ),
                ),
                add_provider_form(router.id),
                spacing=SPACING_SMALL,
                align_items="start",
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        value=router.id.to(str),
    )


def models_list() -> rx.Component:
    """Display list of routers."""
    return rx.vstack(
        add_router_form(),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading("Routers", size=HEADING_SIZE_SECTION),
                    rx.badge(
                        ModelsState.routers.length(),
                        variant="soft",
                        color_scheme="blue",
                    ),
                    rx.spacer(),
                    align="center",
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                rx.divider(),
                rx.cond(
                    ModelsState.routers_loading,
                    rx.center(
                        rx.spinner(size=SIZE_MEDIUM),
                        width="100%",
                        padding=PADDING_PAGE,
                    ),
                    rx.cond(
                        ModelsState.routers.length() > 0,
                        rx.accordion.root(
                            rx.foreach(ModelsState.routers_with_formatted_dates, router_accordion_item),
                            collapsible=True,
                            width="100%",
                            variant="ghost",
                            style={
                                "& button[data-state] > svg": {
                                    "display": "none",
                                },
                            },
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("container", size=ICON_SIZE_EMPTY_STATE, color=rx.color("mauve", 8)),
                                rx.text(
                                    "No routers yet",
                                    size=TEXT_SIZE_LARGE,
                                    color=rx.color("mauve", 10),
                                ),
                                rx.text(
                                    "Create your first router to get started",
                                    size=TEXT_SIZE_LABEL,
                                    color=rx.color("mauve", 9),
                                ),
                                spacing=SPACING_SMALL,
                            ),
                            width="100%",
                            padding=PADDING_PAGE,
                        ),
                    ),
                ),
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            width="100%",
        ),
        delete_provider_dialog(),
        spacing=SPACING_LARGE,
        width="100%",
    )
