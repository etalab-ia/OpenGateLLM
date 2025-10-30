"""Roles limits management component."""

import reflex as rx

from app.features.roles.models import Limit
from app.features.roles.state import RolesState


def limit_row(limit: Limit) -> rx.Component:
    """Display a single limit row."""
    return rx.table.row(
        rx.table.cell(
            rx.text(
                limit.model,
                size="3",
                weight="medium",
                color=rx.color("mauve", 12),
            ),
        ),
        rx.table.cell(
            rx.badge(
                limit.type.upper(),
                variant="soft",
                color_scheme="blue",
            ),
        ),
        rx.table.cell(
            rx.text(
                rx.cond(
                    limit.value,
                    limit.value.to(str),
                    "Unlimited",
                ),
                size="3",
                color=rx.color("mauve", 11),
            ),
        ),
        rx.table.cell(
            rx.button(
                rx.icon("trash-2", size=18),
                on_click=lambda: RolesState.delete_limit(limit.model, limit.type),
                variant="soft",
                color_scheme="red",
                size="2",
                disabled=RolesState.delete_limit_loading,
            ),
            justify="end",
        ),
        align="center",
    )


def add_limit_form() -> rx.Component:
    """Form to add a new limit."""
    return rx.vstack(
        rx.hstack(
            rx.select(
                RolesState.available_models,
                placeholder="Select model",
                value=RolesState.new_limit_model,
                on_change=RolesState.set_new_limit_model,
                disabled=RolesState.add_limit_loading,
                width="30%",
            ),
            rx.select(
                RolesState.available_limit_types,
                value=RolesState.new_limit_type,
                on_change=RolesState.set_new_limit_type,
                disabled=RolesState.add_limit_loading,
            ),
            rx.input(
                placeholder="Value (empty = unlimited)",
                value=RolesState.new_limit_value,
                on_change=RolesState.set_new_limit_value,
                disabled=RolesState.add_limit_loading,
                type="number",
                flex="1",
            ),
            rx.button(
                rx.cond(
                    RolesState.add_limit_loading,
                    rx.spinner(size="3"),
                    "Create",
                ),
                on_click=RolesState.add_limit,
                disabled=RolesState.add_limit_loading | ~RolesState.has_limits_selected_role,
            ),
            width="100%",
            spacing="2",
        ),
        spacing="3",
        width="100%",
    )


def roles_limits() -> rx.Component:
    """Display and manage limits for selected role."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Rate limits", size="6"),
                rx.spacer(),
                rx.text("Role", size="2", color=rx.color("mauve", 11)),
                rx.select.root(
                    rx.select.trigger(placeholder="Select a role", size="2", width="200px"),
                    rx.select.content(
                        rx.foreach(
                            RolesState.roles,
                            lambda role: rx.select.item(role.name, value=role.id.to(str)),
                        ),
                    ),
                    value=rx.cond(
                        RolesState.limits_selected_role_id,
                        RolesState.limits_selected_role_id.to(str),
                        "",
                    ),
                    on_change=RolesState.set_limits_selected_role,
                ),
                rx.text("Model", size="2", color=rx.color("mauve", 11)),
                rx.select(
                    RolesState.limits_models_list_with_all,
                    value=RolesState.limits_filter_model,
                    on_change=RolesState.set_limits_filter_model,
                    placeholder="All models",
                    size="2",
                ),
                align="center",
                spacing="2",
                width="100%",
            ),
            rx.divider(),
            rx.cond(
                ~RolesState.has_limits_selected_role,
                rx.center(
                    rx.vstack(
                        rx.icon("arrow-up", size=48, color=rx.color("mauve", 8)),
                        rx.text(
                            "Select a role first",
                            size="4",
                            color=rx.color("mauve", 10),
                        ),
                        rx.text(
                            "Choose a role from the dropdown above to manage its limits",
                            size="2",
                            color=rx.color("mauve", 9),
                        ),
                        spacing="2",
                    ),
                    width="100%",
                    padding="2em",
                ),
                rx.cond(
                    RolesState.filtered_limits.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Model", min_width="300px"),
                                rx.table.column_header_cell("Type", min_width="120px"),
                                rx.table.column_header_cell("Value", min_width="120px"),
                                rx.table.column_header_cell(justify="end", min_width="100px"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(RolesState.filtered_limits, limit_row),
                        ),
                        variant="surface",
                        width="100%",
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon("gauge", size=48, color=rx.color("mauve", 8)),
                            rx.text(
                                "No limits",
                                size="4",
                                color=rx.color("mauve", 10),
                            ),
                            rx.text(
                                rx.cond(
                                    RolesState.limits_filter_model == "all",
                                    "This role has no limits configured",
                                    "No limits for the selected model",
                                ),
                                size="2",
                                color=rx.color("mauve", 9),
                            ),
                            spacing="2",
                        ),
                        width="100%",
                        padding="2em",
                    ),
                ),
            ),
            add_limit_form(),
            spacing="3",
            width="100%",
        ),
        width="100%",
        max_width="1000px",
    )
