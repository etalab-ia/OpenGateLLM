import reflex as rx

from app.core.variables import (
    HEADING_SIZE_FORM,
    HEADING_SIZE_SECTION,
    ICON_SIZE_EMPTY_STATE,
    ICON_SIZE_MEDIUM,
    MARGIN_MEDIUM,
    MAX_DIALOG_WIDTH,
    PADDING_PAGE,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_NONE,
    SPACING_SMALL,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_LARGE,
)
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
                        "Role: " + user.role.to(str),
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 10),
                    ),
                    rx.cond(
                        user.organization,
                        rx.fragment(
                            rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                            rx.text(
                                "Org: " + user.organization.to(str),
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


def create_user_form() -> rx.Component:
    """Form to create a new user."""
    return rx.card(
        rx.vstack(
            rx.heading("Create new user", size=HEADING_SIZE_FORM),
            rx.grid(
                rx.vstack(
                    rx.text("Email *", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="user@example.com",
                        value=UsersState.new_user_email,
                        on_change=UsersState.set_new_user_email,
                        disabled=UsersState.create_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Name", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="User name",
                        value=UsersState.new_user_name,
                        on_change=UsersState.set_new_user_name,
                        disabled=UsersState.create_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Password *", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Password",
                        type="password",
                        value=UsersState.new_user_password,
                        on_change=UsersState.set_new_user_password,
                        disabled=UsersState.create_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Role *", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.select.root(
                        rx.select.trigger(placeholder="Select role", width="100%"),
                        rx.select.content(
                            rx.foreach(
                                UsersState.available_roles,
                                lambda role: rx.select.item(role["name"], value=role["id"].to(str)),
                            ),
                        ),
                        value=UsersState.new_user_role,
                        on_change=UsersState.set_new_user_role,
                        disabled=UsersState.create_user_loading,
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Organization", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.select.root(
                        rx.select.trigger(placeholder="None (optional)", width="100%"),
                        rx.select.content(
                            rx.foreach(
                                UsersState.available_organizations,
                                lambda org: rx.select.item(org["name"], value=org["id"].to(str)),
                            ),
                        ),
                        value=UsersState.new_user_organization,
                        on_change=UsersState.set_new_user_organization,
                        disabled=UsersState.create_user_loading,
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Budget", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Budget (empty = unlimited)",
                        type="number",
                        value=UsersState.new_user_budget,
                        on_change=UsersState.set_new_user_budget,
                        disabled=UsersState.create_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Expires at (timestamp)", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Timestamp (empty = never)",
                        type="number",
                        value=UsersState.new_user_expires_at,
                        on_change=UsersState.set_new_user_expires_at,
                        disabled=UsersState.create_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Priority", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="0",
                        type="number",
                        value=UsersState.new_user_priority,
                        on_change=UsersState.set_new_user_priority,
                        disabled=UsersState.create_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                columns="2",
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(
                        UsersState.create_user_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Create User",
                    ),
                    on_click=UsersState.create_user,
                    disabled=UsersState.create_user_loading,
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        width="100%",
    )


def edit_user_dialog() -> rx.Component:
    """Dialog for editing a user."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Edit User"),
            rx.dialog.description(
                "Update user information. Leave fields empty to keep current values.",
            ),
            rx.grid(
                rx.vstack(
                    rx.text("Email", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="user@example.com",
                        value=UsersState.edit_user_email,
                        on_change=UsersState.set_edit_user_email,
                        disabled=UsersState.edit_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Name", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="User name",
                        value=UsersState.edit_user_name,
                        on_change=UsersState.set_edit_user_name,
                        disabled=UsersState.edit_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("New Password", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Leave empty to keep current",
                        type="password",
                        value=UsersState.edit_user_password,
                        on_change=UsersState.set_edit_user_password,
                        disabled=UsersState.edit_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Role", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.select.root(
                        rx.select.trigger(placeholder="Select role", width="100%"),
                        rx.select.content(
                            rx.foreach(
                                UsersState.available_roles,
                                lambda role: rx.select.item(role["name"], value=role["id"].to(str)),
                            ),
                        ),
                        value=UsersState.edit_user_role,
                        on_change=UsersState.set_edit_user_role,
                        disabled=UsersState.edit_user_loading,
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Organization", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.select.root(
                        rx.select.trigger(placeholder="None (optional)", width="100%"),
                        rx.select.content(
                            rx.foreach(
                                UsersState.available_organizations,
                                lambda org: rx.select.item(org["name"], value=org["id"].to(str)),
                            ),
                        ),
                        value=UsersState.edit_user_organization,
                        on_change=UsersState.set_edit_user_organization,
                        disabled=UsersState.edit_user_loading,
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Budget", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Budget (empty = unlimited)",
                        type="number",
                        value=UsersState.edit_user_budget,
                        on_change=UsersState.set_edit_user_budget,
                        disabled=UsersState.edit_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Expires at (timestamp)", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="Timestamp (empty = never)",
                        type="number",
                        value=UsersState.edit_user_expires_at,
                        on_change=UsersState.set_edit_user_expires_at,
                        disabled=UsersState.edit_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Priority", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.input(
                        placeholder="0",
                        type="number",
                        value=UsersState.edit_user_priority,
                        on_change=UsersState.set_edit_user_priority,
                        disabled=UsersState.edit_user_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                columns="2",
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=lambda: UsersState.set_user_to_edit(None),
                    ),
                ),
                rx.button(
                    rx.cond(
                        UsersState.edit_user_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Update",
                    ),
                    on_click=UsersState.update_user,
                    disabled=UsersState.edit_user_loading,
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
                margin_top=MARGIN_MEDIUM,
            ),
            max_width=MAX_DIALOG_WIDTH,
        ),
        open=UsersState.is_edit_user_dialog_open,
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
            rx.select.trigger(placeholder="All roles", size="2", width="150px"),
            rx.select.content(
                rx.foreach(
                    UsersState.available_roles,
                    lambda role: rx.select.item(role["name"], value=role["id"].to(str)),
                ),
            ),
            value=rx.cond(
                UsersState.filter_role,
                UsersState.filter_role.to(str),
                "",
            ),
            on_change=UsersState.set_filter_role,
        ),
        rx.select.root(
            rx.select.trigger(placeholder="All organizations", size="2", width="150px"),
            rx.select.content(
                rx.foreach(
                    UsersState.available_organizations,
                    lambda org: rx.select.item(org["name"], value=org["id"].to(str)),
                ),
            ),
            value=rx.cond(
                UsersState.filter_organization,
                UsersState.filter_organization.to(str),
                "",
            ),
            on_change=UsersState.set_filter_organization,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def users_list() -> rx.Component:
    """Display list of users with sorting and pagination."""
    return rx.vstack(
        create_user_form(),
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
        edit_user_dialog(),
        delete_user_dialog(),
        spacing=SPACING_LARGE,
        width="100%",
    )
