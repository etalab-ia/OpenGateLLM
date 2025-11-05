import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    ICON_SIZE_EMPTY_STATE,
    ICON_SIZE_MEDIUM,
    PADDING_PAGE,
    SELECT_MEDIUM_WIDTH,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_NONE,
    SPACING_SMALL,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_LARGE,
)
from app.features.users.components.user_update_form import user_update_form
from app.features.users.components.users_pagination import users_pagination
from app.features.users.models import FormattedUser
from app.features.users.state import UsersState


def user_item(user: FormattedUser) -> rx.Component:
    """Display a single user item."""
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        user.email,
                        size=TEXT_SIZE_LARGE,
                        weight="bold",
                        color=rx.color("mauve", 12),
                    ),
                    rx.badge(
                        user.id.to(str),
                        variant="soft",
                        color_scheme="blue",
                    ),
                    rx.cond(
                        user.name,
                        rx.badge(
                            user.name,
                            variant="soft",
                            color_scheme="green",
                        ),
                    ),
                    rx.badge(
                        "Priority: " + user.priority.to(str),
                        variant="soft",
                        color_scheme="purple",
                    ),
                    spacing=SPACING_SMALL,
                ),
                rx.hstack(
                    rx.text(
                        "Role: " + user.role_name,
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 10),
                    ),
                    rx.cond(
                        user.organization_name,
                        rx.fragment(
                            rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                            rx.text(
                                "Org: " + user.organization_name,
                                size=TEXT_SIZE_LABEL,
                                color=rx.color("mauve", 10),
                            ),
                        ),
                    ),
                    rx.cond(
                        user.budget,
                        rx.fragment(
                            rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                            rx.text(
                                "Budget: " + user.budget.to(str),
                                size=TEXT_SIZE_LABEL,
                                color=rx.color("mauve", 10),
                            ),
                        ),
                    ),
                    spacing=SPACING_SMALL,
                ),
                rx.hstack(
                    rx.text(
                        f"Created: {user.created_at}",
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 9),
                    ),
                    rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                    rx.text(
                        f"Updated: {user.updated_at}",
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 9),
                    ),
                    rx.cond(
                        user.expires_at_formatted,
                        rx.fragment(
                            rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                            rx.text(
                                "Expires: " + user.expires_at_formatted,
                                size=TEXT_SIZE_LABEL,
                                color=rx.color("red", 10),
                            ),
                        ),
                    ),
                    spacing=SPACING_SMALL,
                ),
                spacing=SPACING_SMALL,
                align_items="start",
                flex="1",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("pencil", size=ICON_SIZE_MEDIUM),
                    on_click=lambda: UsersState.set_user_to_edit(user.id),
                    variant="soft",
                    color_scheme="blue",
                    size="2",
                ),
                rx.button(
                    rx.icon("trash-2", size=ICON_SIZE_MEDIUM),
                    on_click=lambda: UsersState.set_user_to_delete(user.id),
                    variant="soft",
                    color_scheme="red",
                    size="2",
                ),
                spacing=SPACING_SMALL,
            ),
            width="100%",
            align="center",
            justify="between",
            padding_y="0.75em",
        ),
        rx.divider(),
        width="100%",
    )


def delete_user_dialog() -> rx.Component:
    """Dialog for deleting a user."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete User"),
            rx.alert_dialog.description(
                "Are you sure you want to delete this user? This action cannot be undone.",
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=lambda: UsersState.set_user_to_delete(None),
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        rx.cond(
                            UsersState.delete_user_loading,
                            rx.spinner(size=SIZE_MEDIUM),
                            "Delete",
                        ),
                        on_click=lambda: UsersState.delete_user(UsersState.user_to_delete),
                        color_scheme="red",
                        disabled=UsersState.delete_user_loading,
                    ),
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
            ),
            spacing=SPACING_LARGE,
        ),
        open=UsersState.is_delete_user_dialog_open,
    )


def users_sorting() -> rx.Component:
    """Sorting controls for users."""
    return rx.hstack(
        rx.text("Sort by", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select(
            ["id", "name", "created_at", "updated_at"],
            value=UsersState.users_order_by,
            on_change=UsersState.set_users_order_by,
        ),
        rx.select(
            ["asc", "desc"],
            value=UsersState.users_order_direction,
            on_change=UsersState.set_users_order_direction,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def users_filters() -> rx.Component:
    """Filters for users list."""
    return rx.hstack(
        rx.text("Filters", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select.root(
            rx.select.trigger(size="2", width=SELECT_MEDIUM_WIDTH),
            rx.select.content(
                rx.select.item("All roles", value="all"),
                rx.foreach(
                    UsersState.available_roles,
                    lambda role: rx.select.item(role["name"], value=role["id"].to(str)),
                ),
            ),
            value=UsersState.filter_role_value,
            on_change=UsersState.set_filter_role,
        ),
        rx.select.root(
            rx.select.trigger(size="2", width=SELECT_MEDIUM_WIDTH),
            rx.select.content(
                rx.select.item("All organizations", value="none"),
                rx.foreach(
                    UsersState.available_organizations,
                    lambda org: rx.select.item(org["name"], value=org["id"].to(str)),
                ),
            ),
            value=UsersState.filter_organization_value,
            on_change=UsersState.set_filter_organization,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def users_list() -> rx.Component:
    """Display list of users with sorting and pagination."""
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading("Users", size=HEADING_SIZE_SECTION),
                    rx.badge(
                        UsersState.users.length(),
                        variant="soft",
                        color_scheme="blue",
                    ),
                    rx.spacer(),
                    users_filters(),
                    users_sorting(),
                    align="center",
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                rx.divider(),
                rx.cond(
                    UsersState.users_loading,
                    rx.center(
                        rx.spinner(size=SIZE_MEDIUM),
                        width="100%",
                        padding=PADDING_PAGE,
                    ),
                    rx.cond(
                        UsersState.users.length() > 0,
                        rx.vstack(
                            rx.foreach(UsersState.users_with_formatted_dates, user_item),
                            spacing=SPACING_NONE,
                            width="100%",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("users", size=ICON_SIZE_EMPTY_STATE, color=rx.color("mauve", 8)),
                                rx.text(
                                    "No users yet",
                                    size=TEXT_SIZE_LARGE,
                                    color=rx.color("mauve", 10),
                                ),
                                rx.text(
                                    "Create your first user to get started",
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
                rx.cond(
                    UsersState.users.length() > 0,
                    rx.hstack(
                        users_pagination(),
                        width="100%",
                        justify="end",
                    ),
                ),
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            width="100%",
        ),
        user_update_form(),
        delete_user_dialog(),
        spacing=SPACING_LARGE,
        width="100%",
    )
