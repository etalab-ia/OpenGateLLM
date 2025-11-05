import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    ICON_SIZE_EMPTY_STATE,
    ICON_SIZE_MEDIUM,
    ICON_SIZE_TINY,
    PADDING_PAGE,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_SMALL,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_LARGE,
    TEXT_SIZE_MEDIUM,
)
from app.features.roles.components.role_update_form import role_update_form
from app.features.roles.components.roles_pagination import roles_pagination
from app.features.roles.models import FormattedRole
from app.features.roles.state import RolesState


def limit_value_cell(value) -> rx.Component:
    """Display a limit value cell."""
    return rx.table.cell(
        rx.cond(
            value,
            rx.text(value.to(str), weight="medium", size=TEXT_SIZE_LABEL),
            rx.text("Unlimited", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        ),
    )


def model_limits_row(role_id: int, model: str) -> rx.Component:
    """Display a row with all limits for a model."""
    limits = RolesState.roles_limits_by_model[role_id][model]

    return rx.table.row(
        rx.table.cell(
            rx.text(
                model,
                size=TEXT_SIZE_LABEL,
                weight="medium",
                color=rx.color("mauve", 12),
            ),
        ),
        limit_value_cell(limits["rpm"]),
        limit_value_cell(limits["rpd"]),
        limit_value_cell(limits["tpm"]),
        limit_value_cell(limits["tpd"]),
        rx.table.cell(
            rx.button(
                rx.icon("trash-2", size=ICON_SIZE_MEDIUM),
                on_click=lambda: RolesState.delete_model_limits(role_id, model),
                variant="soft",
                color_scheme="red",
                size=TEXT_SIZE_LABEL,
                disabled=RolesState.delete_limit_loading,
            ),
            justify="end",
        ),
        align="center",
    )


def add_limit_form(role_id: int) -> rx.Component:
    """Form to add limits for a model (all 4 types)."""
    return rx.card(
        rx.vstack(
            rx.heading("Add limits for a model", size=TEXT_SIZE_MEDIUM),
            rx.divider(),
            rx.hstack(
                rx.vstack(
                    rx.text("Model *", size=TEXT_SIZE_LABEL, weight="bold"),
                    rx.select(
                        RolesState.available_models,
                        placeholder="Select model",
                        value=RolesState.new_limit_model,
                        on_change=RolesState.set_new_limit_model,
                        disabled=RolesState.add_limit_loading,
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.tooltip(
                        rx.hstack(
                            rx.text("RPM", size=TEXT_SIZE_LABEL, weight="bold"),
                            rx.icon("info", size=ICON_SIZE_TINY),
                            spacing=SPACING_TINY,
                            align="center",
                        ),
                        content="Requests Per Minute",
                    ),
                    rx.input(
                        placeholder="Unlimited",
                        value=RolesState.new_limit_rpm,
                        on_change=RolesState.set_new_limit_rpm,
                        disabled=RolesState.add_limit_loading,
                        type="number",
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.tooltip(
                        rx.hstack(
                            rx.text("RPD", size=TEXT_SIZE_LABEL, weight="bold"),
                            rx.icon("info", size=ICON_SIZE_TINY),
                            spacing=SPACING_TINY,
                            align="center",
                        ),
                        content="Requests Per Day",
                    ),
                    rx.input(
                        placeholder="Unlimited",
                        value=RolesState.new_limit_rpd,
                        on_change=RolesState.set_new_limit_rpd,
                        disabled=RolesState.add_limit_loading,
                        type="number",
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.tooltip(
                        rx.hstack(
                            rx.text("TPM", size=TEXT_SIZE_LABEL, weight="bold"),
                            rx.icon("info", size=ICON_SIZE_TINY),
                            spacing=SPACING_TINY,
                            align="center",
                        ),
                        content="Tokens Per Minute",
                    ),
                    rx.input(
                        placeholder="Unlimited",
                        value=RolesState.new_limit_tpm,
                        on_change=RolesState.set_new_limit_tpm,
                        disabled=RolesState.add_limit_loading,
                        type="number",
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                rx.vstack(
                    rx.tooltip(
                        rx.hstack(
                            rx.text("TPD", size=TEXT_SIZE_LABEL, weight="bold"),
                            rx.icon("info", size=ICON_SIZE_TINY),
                            spacing=SPACING_TINY,
                            align="center",
                        ),
                        content="Tokens Per Day",
                    ),
                    rx.input(
                        placeholder="Unlimited",
                        value=RolesState.new_limit_tpd,
                        on_change=RolesState.set_new_limit_tpd,
                        disabled=RolesState.add_limit_loading,
                        type="number",
                        width="100%",
                    ),
                    spacing=SPACING_TINY,
                    width="100%",
                ),
                spacing=SPACING_SMALL,
                width="100%",
            ),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.cond(
                        RolesState.add_limit_loading,
                        rx.spinner(size=SIZE_MEDIUM),
                        "Add limits",
                    ),
                    on_click=lambda: RolesState.add_limit(role_id),
                    disabled=RolesState.add_limit_loading,
                ),
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        variant="surface",
        width="100%",
    )


def role_limits_table_compact(role: FormattedRole) -> rx.Component:
    """Compact limits table for a specific role."""
    models_list = RolesState.roles_models_lists[role.id]

    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Model"),
                rx.table.column_header_cell(
                    rx.tooltip(
                        rx.hstack(
                            rx.text("RPM"),
                            rx.icon("info", size=ICON_SIZE_TINY),
                            spacing=SPACING_TINY,
                            align="center",
                        ),
                        content="Requests Per Minute",
                    ),
                ),
                rx.table.column_header_cell(
                    rx.tooltip(
                        rx.hstack(
                            rx.text("RPD"),
                            rx.icon("info", size=ICON_SIZE_TINY),
                            spacing=SPACING_TINY,
                            align="center",
                        ),
                        content="Requests Per Day",
                    ),
                ),
                rx.table.column_header_cell(
                    rx.tooltip(
                        rx.hstack(
                            rx.text("TPM"),
                            rx.icon("info", size=ICON_SIZE_TINY),
                            spacing=SPACING_TINY,
                            align="center",
                        ),
                        content="Tokens Per Minute",
                    ),
                ),
                rx.table.column_header_cell(
                    rx.tooltip(
                        rx.hstack(
                            rx.text("TPD"),
                            rx.icon("info", size=ICON_SIZE_TINY),
                            spacing=SPACING_TINY,
                            align="center",
                        ),
                        content="Tokens Per Day",
                    ),
                ),
                rx.table.column_header_cell(justify="end"),
            ),
        ),
        rx.table.body(
            rx.foreach(
                models_list,
                lambda model: model_limits_row(role.id, model),
            ),
        ),
        variant="surface",
        width="100%",
    )


def role_accordion_item(role: FormattedRole) -> rx.Component:
    """Display a single role as an accordion item."""
    return rx.accordion.item(
        header=rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            role.name,
                            size=TEXT_SIZE_LARGE,
                            weight="bold",
                            color=rx.color("mauve", 12),
                        ),
                        rx.badge(
                            role.id.to(str),
                            variant="soft",
                            color_scheme="blue",
                        ),
                        rx.badge(
                            role.users.to(str) + " user" + rx.cond(role.users != 1, "s", ""),
                            variant="soft",
                            color_scheme="green",
                        ),
                        spacing=SPACING_SMALL,
                    ),
                    rx.hstack(
                        rx.text(
                            f"Created: {role.created_at}",
                            size=TEXT_SIZE_LABEL,
                            color=rx.color("mauve", 9),
                        ),
                        rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                        rx.text(
                            f"Updated: {role.updated_at}",
                            size=TEXT_SIZE_LABEL,
                            color=rx.color("mauve", 9),
                        ),
                        spacing=SPACING_SMALL,
                    ),
                    rx.hstack(
                        rx.text(
                            role.permissions.length().to(str) + " permission" + rx.cond(role.permissions.length() != 1, "s", ""),
                            size=TEXT_SIZE_LABEL,
                            color=rx.color("mauve", 10),
                        ),
                        rx.text("•", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
                        rx.text(
                            role.limits.length().to(str) + " limit" + rx.cond(role.limits.length() != 1, "s", ""),
                            size=TEXT_SIZE_LABEL,
                            color=rx.color("mauve", 10),
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
                        on_click=lambda: RolesState.set_role_to_edit(role.id),
                        variant="soft",
                        color_scheme="blue",
                        size=TEXT_SIZE_LABEL,
                    ),
                    rx.button(
                        rx.icon("trash-2", size=ICON_SIZE_MEDIUM),
                        on_click=lambda: RolesState.set_role_to_delete(role.id),
                        variant="soft",
                        color_scheme="red",
                        size=TEXT_SIZE_LABEL,
                    ),
                    spacing=SPACING_SMALL,
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
            rx.heading("Special permissions", size=TEXT_SIZE_MEDIUM),
            rx.cond(
                role.permissions.length() > 0,
                rx.hstack(
                    rx.foreach(
                        role.permissions,
                        lambda perm: rx.badge(
                            perm,
                            variant="soft",
                            color_scheme="purple",
                        ),
                    ),
                    spacing=SPACING_SMALL,
                    wrap="wrap",
                ),
                rx.text("No permissions, updated the role to add some.", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 9)),
            ),
            rx.vstack(
                rx.heading("Model limits", size=TEXT_SIZE_MEDIUM),
                rx.cond(
                    role.limits.length() > 0,
                    role_limits_table_compact(role),
                    rx.center(
                        rx.text(
                            "No limits configured",
                            size=TEXT_SIZE_LABEL,
                            color=rx.color("mauve", 9),
                        ),
                        width="100%",
                        padding="1em",
                    ),
                ),
                add_limit_form(role.id),
                spacing=SPACING_SMALL,
                align_items="start",
                width="100%",
            ),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        value=role.id.to(str),
    )


def delete_role_dialog() -> rx.Component:
    """Dialog for deleting a role."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Role"),
            rx.alert_dialog.description("Are you sure you want to delete this role? This action cannot be undone."),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=lambda: RolesState.set_role_to_delete(None),
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        rx.cond(
                            RolesState.delete_role_loading,
                            rx.spinner(size=SIZE_MEDIUM),
                            "Delete",
                        ),
                        on_click=lambda: RolesState.delete_role(RolesState.role_to_delete),
                        color_scheme="red",
                        disabled=RolesState.delete_role_loading,
                    ),
                ),
                spacing=SPACING_MEDIUM,
                justify="end",
            ),
            spacing=SPACING_LARGE,
        ),
        open=RolesState.is_delete_role_dialog_open,
    )


def roles_sorting() -> rx.Component:
    """Sorting controls for roles."""
    return rx.hstack(
        rx.text("Sort by", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select(
            ["id", "name", "created_at", "updated_at"],
            value=RolesState.roles_order_by,
            on_change=RolesState.set_roles_order_by,
        ),
        rx.select(
            ["asc", "desc"],
            value=RolesState.roles_order_direction,
            on_change=RolesState.set_roles_order_direction,
        ),
        spacing=SPACING_SMALL,
        align="center",
    )


def roles_list() -> rx.Component:
    """Display list of roles with sorting and pagination."""
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading("Roles", size=HEADING_SIZE_SECTION),
                    rx.badge(
                        RolesState.roles.length(),
                        variant="soft",
                        color_scheme="blue",
                    ),
                    rx.spacer(),
                    roles_sorting(),
                    align="center",
                    spacing=SPACING_SMALL,
                    width="100%",
                ),
                rx.divider(),
                rx.cond(
                    RolesState.roles_loading,
                    rx.center(
                        rx.spinner(size=SIZE_MEDIUM),
                        width="100%",
                        padding=PADDING_PAGE,
                    ),
                    rx.cond(
                        RolesState.roles.length() > 0,
                        rx.accordion.root(
                            rx.foreach(RolesState.roles_with_formatted_dates, role_accordion_item),
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
                                rx.icon("shield", size=ICON_SIZE_EMPTY_STATE, color=rx.color("mauve", 8)),
                                rx.text(
                                    "No roles yet",
                                    size=TEXT_SIZE_LARGE,
                                    color=rx.color("mauve", 10),
                                ),
                                rx.text(
                                    "Create your first role to get started",
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
                    RolesState.roles.length() > 0,
                    rx.hstack(
                        roles_pagination(),
                        width="100%",
                        justify="end",
                    ),
                ),
                spacing=SPACING_MEDIUM,
                width="100%",
            ),
            width="100%",
        ),
        role_update_form(),
        delete_role_dialog(),
        spacing=SPACING_LARGE,
        width="100%",
    )
