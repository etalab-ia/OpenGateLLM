import reflex as rx

from app.core.variables import SELECT_MEDIUM_WIDTH, SPACING_SMALL, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.providers.components.dialogs import provider_delete_dialog, provider_settings_dialog
from app.features.providers.models import Provider
from app.features.providers.state import ProvidersState
from app.shared.components.lists import entity_list, entity_row


def provider_row_content(provider: Provider) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                provider.model_name,
                size=TEXT_SIZE_LARGE,
                weight="bold",
                color=rx.color("mauve", 12),
            ),
            rx.tooltip(
                rx.badge(
                    provider.id.to(str),
                    variant="soft",
                    color_scheme="blue",
                ),
                content="ID",
            ),
            rx.tooltip(
                rx.badge(
                    provider.router,
                    variant="soft",
                    color_scheme="green",
                ),
                content="Router name",
            ),
            spacing=SPACING_SMALL,
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def provider_row_description(provider: Provider) -> rx.Component:
    return rx.vstack(
        rx.text(
            f"Created: {provider.created} • Owned by: {provider.user}",
            size=TEXT_SIZE_LABEL,
            color=rx.color("mauve", 9),
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def provider_renderer_row(provider: Provider, with_settings: bool = False) -> rx.Component:
    """Display a row with provider information."""
    return entity_row(
        state=ProvidersState,
        entity=provider,
        row_content=provider_row_content(provider),
        row_description=provider_row_description(provider),
        with_settings=with_settings,
    )


def provider_filters() -> rx.Component:
    return rx.hstack(
        rx.text("Filters", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select.root(
            rx.select.trigger(size="2", width=SELECT_MEDIUM_WIDTH),
            rx.select.content(
                rx.select.item("All routers", value="0"),
                rx.foreach(
                    ProvidersState.routers_list,
                    lambda item: rx.select.item(item["name"], value=item["id"].to(str)),
                ),
            ),
            value=ProvidersState.filter_router_value.to(str),
            on_change=lambda value: ProvidersState.set_filter_router(value),
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def providers_list() -> rx.Component:
    """Providers list."""
    return entity_list(
        state=ProvidersState,
        title="Providers",
        entities=ProvidersState.providers,
        renderer_entity_row=provider_renderer_row,
        no_entities_message="No providers yet",
        no_entities_description="Create your first provider to get started",
        settings_dialog=provider_settings_dialog(),
        delete_dialog=provider_delete_dialog(),
        filters=provider_filters(),
        pagination=True,
        sorting=True,
    )
