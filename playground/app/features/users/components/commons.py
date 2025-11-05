import reflex as rx

from app.core.configuration import configuration
from app.core.variables import ICON_SIZE_TINY, SPACING_MEDIUM, SPACING_TINY, TEXT_SIZE_LABEL


def user_form_fields(
    email_value,
    email_on_change,
    name_value,
    name_on_change,
    password_value,
    password_on_change,
    role_value,
    role_on_change,
    organization_value,
    organization_on_change,
    budget_value,
    budget_on_change,
    expires_at_value,
    expires_at_on_change,
    priority_value,
    priority_on_change,
    available_roles,
    available_organizations,
    disabled: bool = False,
    password_placeholder: str = "Password",
    password_required: bool = True,
    email_required: bool = True,
):
    """Generalized user form fields for create and update."""
    return rx.grid(
        rx.vstack(
            rx.text("Email" + (" *" if email_required else ""), size=TEXT_SIZE_LABEL, weight="bold"),
            rx.input(
                placeholder="user@example.com",
                value=email_value,
                on_change=email_on_change,
                disabled=disabled,
                width="100%",
            ),
            spacing=SPACING_TINY,
            width="100%",
        ),
        rx.vstack(
            rx.text("Name", size=TEXT_SIZE_LABEL, weight="bold"),
            rx.input(
                placeholder="User name",
                value=name_value,
                on_change=name_on_change,
                disabled=disabled,
                width="100%",
            ),
            spacing=SPACING_TINY,
            width="100%",
        ),
        rx.vstack(
            rx.text("Password" + (" *" if password_required else ""), size=TEXT_SIZE_LABEL, weight="bold"),
            rx.input(
                placeholder=password_placeholder,
                type="password",
                value=password_value,
                on_change=password_on_change,
                disabled=disabled,
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
                        available_roles,
                        lambda role: rx.select.item(role["name"], value=role["id"].to(str)),
                    ),
                ),
                value=role_value,
                on_change=role_on_change,
                disabled=disabled,
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
                        available_organizations,
                        lambda org: rx.select.item(org["name"], value=org["id"].to(str)),
                    ),
                ),
                value=organization_value,
                on_change=organization_on_change,
                disabled=disabled,
            ),
            spacing=SPACING_TINY,
            width="100%",
        ),
        rx.vstack(
            rx.hstack(
                rx.text("Budget", size=TEXT_SIZE_LABEL, weight="bold"),
                rx.tooltip(
                    rx.icon("info", size=ICON_SIZE_TINY, color=rx.color("mauve", 10)),
                    content="If budget is empty, the user will have unlimited usage.",
                ),
                spacing=SPACING_TINY,
                align="center",
            ),
            rx.input(
                placeholder="Budget (optional)",
                type="number",
                value=budget_value,
                on_change=budget_on_change,
                disabled=disabled,
                width="100%",
            ),
            spacing=SPACING_TINY,
            width="100%",
        ),
        rx.vstack(
            rx.hstack(
                rx.text("Expires at", size=TEXT_SIZE_LABEL, weight="bold"),
                rx.tooltip(
                    rx.icon("info", size=ICON_SIZE_TINY, color=rx.color("mauve", 10)),
                    content="User account expiration date. Leave empty for no expiration.",
                ),
                spacing=SPACING_TINY,
                align="center",
            ),
            rx.input(
                placeholder="Select date (optional)",
                type="date",
                value=expires_at_value,
                on_change=expires_at_on_change,
                disabled=disabled,
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
                value=priority_value,
                on_change=priority_on_change,
                disabled=disabled,
                width="100%",
                min=0,
                max=configuration.settings.celery_task_max_priority,
            ),
            spacing=SPACING_TINY,
            width="100%",
        ),
        columns="2",
        spacing=SPACING_MEDIUM,
        width="100%",
    )
