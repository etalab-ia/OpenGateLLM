import reflex as rx

from app.core.variables import SELECT_LARGE_WIDTH, SELECT_MEDIUM_WIDTH, SPACING_SMALL, TEXT_SIZE_LABEL, TEXT_SIZE_LARGE
from app.features.users.components.dialogs import user_delete_dialog, user_settings_dialog
from app.features.users.models import User
from app.features.users.state import UsersState
from app.shared.components.lists import entity_list, entity_row


def user_row_content(user: User) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                user.email,
                size=TEXT_SIZE_LARGE,
                weight="bold",
                color=rx.color("mauve", 12),
            ),
            rx.tooltip(
                rx.badge(
                    user.id.to(str),
                    variant="soft",
                    color_scheme="blue",
                ),
                content="ID",
            ),
            spacing=SPACING_SMALL,
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def user_row_description(user: User) -> rx.Component:
    return rx.vstack(
        rx.text(
            f"Created: {user.created} • Updated: {user.updated}",
            size=TEXT_SIZE_LABEL,
            color=rx.color("mauve", 9),
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def user_renderer_row(user: User, with_settings: bool = False) -> rx.Component:
    """Display a row with user information."""
    return entity_row(
        state=UsersState,
        entity=user,
        row_content=user_row_content(user),
        row_description=user_row_description(user),
        with_settings=with_settings,
    )


def user_filters() -> rx.Component:
    """Filters for users list."""
    return rx.hstack(
        rx.text("Search", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.input(
            type="text",
            value=UsersState.search_email_value,
            on_change=UsersState.set_search_email,
            placeholder="Enter email",
            width=SELECT_LARGE_WIDTH,
        ),
        rx.text("Filters", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select(
            UsersState.roles_name_list,
            on_change=UsersState.set_filter_role,
            value=UsersState.filter_role_value,
            width=SELECT_MEDIUM_WIDTH,
        ),
        rx.select(
            UsersState.organizations_name_list,
            on_change=UsersState.set_filter_organization,
            value=UsersState.filter_organization_value,
            width=SELECT_MEDIUM_WIDTH,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def users_list() -> rx.Component:
    """Users list."""
    return entity_list(
        state=UsersState,
        title="Users",
        entities=UsersState.users,
        renderer_entity_row=user_renderer_row,
        no_entities_message="No users yet",
        no_entities_description="Create your first user to get started",
        settings_dialog=user_settings_dialog(),
        delete_dialog=user_delete_dialog(),
        filters=user_filters(),
        pagination=True,
        sorting=True,
    )
