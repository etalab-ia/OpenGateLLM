import reflex as rx

from app.core.variables import SPACING_SMALL, SPACING_TINY, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.routers.components.dialogs import router_delete_dialog, router_edit_dialog
from app.features.routers.models import Router
from app.features.routers.state import RoutersState
from app.shared.components.lists import entity_item_row, entity_list


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
            rx.tooltip(
                rx.badge(
                    router.type.to(str),
                    variant="soft",
                    color_scheme="orange",
                ),
                content="Type",
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
            rx.text("Aliases", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 10)),
            rx.foreach(
                router.aliases,
                lambda alias: rx.badge(
                    alias,
                    variant="outline",
                    color_scheme="gray",
                ),
            ),
            spacing=SPACING_TINY,
        ),
        rx.hstack(
            rx.text("Load Balancing Strategy", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 10)),
            rx.badge(
                router.load_balancing_strategy,
                variant="outline",
                color_scheme="gray",
            ),
            spacing=SPACING_TINY,
        ),
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


def router_row(router: Router) -> rx.Component:
    """Display a row with router information."""
    return entity_item_row(
        state=RoutersState,
        entity=router,
        row_content=router_row_content(router),
        row_description=router_row_description(router),
        with_edit=True,
    )


def routers_list() -> rx.Component:
    """Providers list."""
    return entity_list(
        state=RoutersState,
        title="Routers",
        entities=RoutersState.routers,
        renderer_entity_row=router_row,
        # info_dialog=router_info_dialog(),
        edit_dialog=router_edit_dialog(),
        delete_dialog=router_delete_dialog(),
        no_entities_message="No routers yet",
        no_entities_description="Create your first router to get started",
        pagination=False,
    )
