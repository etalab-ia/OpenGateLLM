import reflex as rx

from app.core.variables import SPACING_SMALL, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.roles.components.dialogs import role_delete_dialog, role_settings_dialog
from app.features.roles.models import Role
from app.features.roles.state import RolesState
from app.shared.components.lists import entity_item_row, entity_list


def role_row_content(role: Role) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                role.name,
                size=TEXT_SIZE_LARGE,
                weight="bold",
                color=rx.color("mauve", 12),
            ),
            rx.tooltip(
                rx.badge(
                    role.id.to(str),
                    variant="soft",
                    color_scheme="blue",
                ),
                content="ID",
            ),
            rx.badge(
                role.users.to(str) + " user" + rx.cond(role.users != 1, "s", ""),
                variant="soft",
                color_scheme="green",
            ),
            spacing=SPACING_SMALL,
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def role_row_description(role: Role) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(f"Created: {role.created} • Updated: {role.updated}"),
            size=TEXT_SIZE_LABEL,
            color=rx.color("mauve", 9),
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def role_row(role: Role, with_settings: bool = False) -> rx.Component:
    """Display a row with role information."""
    return entity_item_row(
        state=RolesState,
        entity=role,
        row_content=role_row_content(role),
        row_description=role_row_description(role),
        with_settings=with_settings,
    )


def roles_list() -> rx.Component:
    """Roles list."""
    return entity_list(
        state=RolesState,
        title="Roles",
        entities=RolesState.roles,
        renderer_entity_row=role_row,
        settings_dialog=role_settings_dialog(),
        delete_dialog=role_delete_dialog(),
        no_entities_message="No roles yet",
        no_entities_description="Create your first role to get started",
        sorting=True,
        pagination=True,
    )
