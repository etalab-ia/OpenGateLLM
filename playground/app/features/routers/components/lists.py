import reflex as rx

from app.core.variables import SPACING_SMALL, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.routers.components.dialogs import router_delete_dialog, router_settings_dialog
from app.features.routers.models import Router
from app.features.routers.state import RoutersState
from app.shared.components.lists import entity_list, entity_row


def router_row_content(router: Router) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                router.name,
                size=TEXT_SIZE_LARGE,
                weight="bold",
                color=rx.color("mauve", 12),
            ),
            rx.tooltip(
                rx.badge(
                    router.id.to(str),
                    variant="soft",
                    color_scheme="blue",
                ),
                content="ID",
            ),
            rx.badge(
                router.providers.to(str) + " provider" + rx.cond(router.providers != 1, "s", ""),
                variant="soft",
                color_scheme="green",
            ),
            spacing=SPACING_SMALL,
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def router_row_description(router: Router) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                f"Created: {router.created} • Updated: {router.updated} • Owned by: {router.user}",
                size=TEXT_SIZE_LABEL,
                color=rx.color("mauve", 9),
            ),
            spacing=SPACING_SMALL,
            align_items="start",
            flex="1",
        ),
    )


def router_renderer_row(router: Router, with_settings: bool = False) -> rx.Component:
    """Display a row with router information."""
    return entity_row(
        state=RoutersState,
        entity=router,
        row_content=router_row_content(router),
        row_description=router_row_description(router),
        with_settings=with_settings,
    )


def routers_list() -> rx.Component:
    """Providers list."""
    return entity_list(
        state=RoutersState,
        title="Routers",
        entities=RoutersState.routers,
        renderer_entity_row=router_renderer_row,
        settings_dialog=router_settings_dialog(),
        no_entities_message="No routers yet",
        no_entities_description="Create your first router to get started",
        delete_dialog=router_delete_dialog(),
        pagination=True,
        sorting=True,
    )
