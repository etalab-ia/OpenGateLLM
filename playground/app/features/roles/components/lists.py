import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    ICON_SIZE_EMPTY_STATE,
    ICON_SIZE_MEDIUM,
    ICON_SIZE_TINY,
    PADDING_MEDIUM,
    PADDING_PAGE,
    SIZE_MEDIUM,
    SPACING_LARGE,
    SPACING_NONE,
    SPACING_SMALL,
    SPACING_TINY,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_LARGE,
    TEXT_SIZE_MEDIUM,
)
from app.features.roles.components.dialogs import role_delete_dialog, role_settings_dialog
from app.features.roles.components.forms import role_create_limit_form
from app.features.roles.models import Role
from app.features.roles.state import RolesState
from app.shared.components.lists import entity_pagination, entity_row, entity_sorting


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
            rx.text(
                f"Created: {role.created} • Updated: {role.updated} • {RolesState.permission_counters[role.id].to(str)} permission"
                + rx.cond(RolesState.permission_counters[role.id] != 1, "s", "")
                + " • "
                + role.limits.length().to(str)
                + " limit"
                + rx.cond(role.limits.length() != 1, "s", ""),
                size=TEXT_SIZE_LABEL,
                color=rx.color("mauve", 9),
            ),
            spacing=SPACING_SMALL,
        ),
        spacing=SPACING_SMALL,
        align_items="start",
        flex="1",
    )


def role_limits_row(role: Role, limit: dict) -> rx.Component:
    """Display a row with all limits for a model."""
    return rx.table.row(
        rx.table.cell(
            rx.text(
                limit["router"],
                size=TEXT_SIZE_LABEL,
                weight="medium",
                color=rx.color("mauve", 12),
            ),
        ),
        rx.table.cell(
            rx.cond(
                limit["rpm"],
                rx.text(limit["rpm"].to(str), weight="medium", size=TEXT_SIZE_LABEL),
                rx.text("Unlimited", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
            ),
        ),
        rx.table.cell(
            rx.cond(
                limit["rpd"],
                rx.text(limit["rpd"].to(str), weight="medium", size=TEXT_SIZE_LABEL),
                rx.text("Unlimited", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
            ),
        ),
        rx.table.cell(
            rx.cond(
                limit["tpm"],
                rx.text(limit["tpm"].to(str), weight="medium", size=TEXT_SIZE_LABEL),
                rx.text("Unlimited", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
            ),
        ),
        rx.table.cell(
            rx.cond(
                limit["tpd"],
                rx.text(limit["tpd"].to(str), weight="medium", size=TEXT_SIZE_LABEL),
                rx.text("Unlimited", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
            ),
        ),
        rx.table.cell(
            rx.button(
                rx.icon("trash-2", size=ICON_SIZE_MEDIUM),
                on_click=lambda: RolesState.delete_limit(role=role, router=limit["router"]),
                variant="soft",
                color_scheme="red",
                size=TEXT_SIZE_LABEL,
            ),
            justify="end",
        ),
        align="center",
    )


def role_limits_list(role: Role) -> rx.Component:
    """Compact limits table for a specific role."""
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Router"),
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
                iterable=role.limits,
                render_fn=lambda limit: role_limits_row(role=role, limit=limit),
            ),
        ),
        variant="surface",
        width="100%",
    )


def role_row(role: Role) -> rx.Component:
    """Display a single role as an accordion item."""
    return rx.accordion.item(
        header=rx.box(
            entity_row(
                entity=role,
                state=RolesState,
                row_content=role_row_content(role=role),
                row_description=role_row_description(role=role),
                with_settings=True,
            ),
            width="100%",
        ),
        content=rx.vstack(
            rx.heading("Limits", size=TEXT_SIZE_MEDIUM),
            rx.cond(
                role.limits.length() > 0,
                role_limits_list(role=role),
                rx.center(
                    rx.text(
                        "No limits configured.",
                        size=TEXT_SIZE_LABEL,
                        color=rx.color("mauve", 9),
                    ),
                    width="100%",
                    padding="1em",
                ),
            ),
            role_create_limit_form(role=role),
            spacing=SPACING_SMALL,
            align_items="start",
            width="100%",
        ),
        value=role.id.to(str),
    )


def roles_list() -> rx.Component:
    """Roles list."""

    state = RolesState
    title = "Roles"
    entities = RolesState.roles
    settings_dialog = role_settings_dialog()
    delete_dialog = role_delete_dialog()
    no_entities_message = "No roles yet"
    no_entities_description = "Create your first role to get started"
    sorting = True
    filters = None
    sorting = True
    pagination = True

    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading(title, size=HEADING_SIZE_SECTION),
                    rx.badge(
                        entities.length(),
                        variant="soft",
                        color_scheme="purple",
                    ),
                    rx.spacer(),
                    filters if filters else rx.fragment(),
                    entity_sorting(state) if sorting else rx.fragment(),
                    align="center",
                    spacing=SPACING_SMALL,
                    width="100%",
                    padding=PADDING_MEDIUM,
                ),
                rx.divider(),
                rx.cond(
                    state.entities_loading,
                    rx.center(
                        rx.spinner(size=SIZE_MEDIUM),
                        width="100%",
                        padding=PADDING_PAGE,
                    ),
                    rx.cond(
                        entities.length() > 0,
                        # Custom change from entity_list to accordion
                        rx.accordion.root(
                            rx.foreach(iterable=entities, render_fn=role_row),
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
                                rx.icon("traffic-cone", size=ICON_SIZE_EMPTY_STATE, color=rx.color("mauve", 8)),
                                rx.text(
                                    no_entities_message,
                                    size=TEXT_SIZE_LARGE,
                                    color=rx.color("mauve", 10),
                                ),
                                rx.text(
                                    no_entities_description,
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
                rx.hstack(
                    entity_pagination(state),
                    width="100%",
                    justify="end",
                    padding=PADDING_MEDIUM,
                )
                if pagination
                else rx.spacer(),
                spacing=SPACING_NONE,
                width="100%",
            ),
            width="100%",
            padding=SPACING_NONE,
        ),
        settings_dialog if settings_dialog else rx.fragment(),
        delete_dialog,
        spacing=SPACING_LARGE,
        width="100%",
    )
