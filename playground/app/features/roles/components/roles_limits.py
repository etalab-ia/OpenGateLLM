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
from app.features.roles.models import Role
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
            ),
            rx.hstack(
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


def role_limits_table(role: Role) -> rx.Component:
    """Table displaying limits for a specific role."""
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


def role_limits_accordion_item(role: Role) -> rx.Component:
    """Accordion item for a single role with its limits table."""
    return rx.accordion.item(
        header=rx.hstack(
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
                role.limits.length().to(str) + " limit" + rx.cond(role.limits.length() != 1, "s", ""),
                variant="soft",
                color_scheme="green",
            ),
            spacing=SPACING_SMALL,
            align="center",
        ),
        content=rx.vstack(
            rx.cond(
                role.limits.length() > 0,
                role_limits_table(role),
                rx.center(
                    rx.vstack(
                        rx.icon("gauge", size=ICON_SIZE_EMPTY_STATE, color=rx.color("mauve", 8)),
                        rx.text(
                            "No limits configured",
                            size=TEXT_SIZE_LARGE,
                            color=rx.color("mauve", 10),
                        ),
                        rx.text(
                            "Add limits for this role using the form below",
                            size=TEXT_SIZE_LABEL,
                            color=rx.color("mauve", 9),
                        ),
                        spacing=SPACING_SMALL,
                    ),
                    width="100%",
                    padding=PADDING_PAGE,
                ),
            ),
            add_limit_form(role.id),
            spacing=SPACING_MEDIUM,
            width="100%",
        ),
        value=role.id.to(str),
    )


def roles_limits() -> rx.Component:
    """Display and manage limits for all roles using accordion."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Rate limits by role", size=HEADING_SIZE_SECTION),
                rx.badge(
                    RolesState.roles.length().to(str) + " role" + rx.cond(RolesState.roles.length() != 1, "s", ""),
                    variant="soft",
                    color_scheme="blue",
                ),
                spacing=SPACING_SMALL,
                align="center",
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
                        rx.foreach(RolesState.roles, role_limits_accordion_item),
                        collapsible=True,
                        width="100%",
                        variant="soft",
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
                                "Create a role first to manage its limits",
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
            spacing=SPACING_LARGE,
            width="100%",
        ),
        width="100%",
    )
