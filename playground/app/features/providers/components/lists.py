import reflex as rx

from app.core.variables import SPACING_SMALL, SPACING_TINY, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.providers.models import Provider
from app.features.providers.state import ProvidersState
from app.shared.components.lists import entity_item_row, entity_list


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
                    provider.type.to(str),
                    variant="soft",
                    color_scheme="green",
                ),
                content="Type",
            ),
            spacing=SPACING_SMALL,
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def provider_row_description(provider: Provider) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.tooltip(
                rx.badge(
                    provider.router,
                    variant="outline",
                    color_scheme="gray",
                ),
                content="Router",
            ),
            rx.tooltip(
                rx.badge(
                    provider.url,
                    variant="outline",
                    color_scheme="gray",
                ),
                content="URL",
            ),
            spacing=SPACING_TINY,
        ),
        rx.text(
            f"Created: {provider.created} • Owned by: {provider.user}",
            size=TEXT_SIZE_LABEL,
            color=rx.color("mauve", 9),
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def provider_row(provider: Provider) -> rx.Component:
    """Display a row with provider information."""
    return entity_item_row(
        state=ProvidersState,
        entity=provider,
        row_content=provider_row_content(provider),
        row_description=provider_row_description(provider),
    )


def providers_list() -> rx.Component:
    """Providers list."""
    return entity_list(
        state=ProvidersState,
        title="Providers",
        entities=ProvidersState.providers,
        renderer_entity_row=provider_row,
        no_entities_message="No providers yet",
        no_entities_description="Create your first provider to get started",
        pagination=False,
    )
