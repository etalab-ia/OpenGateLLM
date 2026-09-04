"""Usage page composition."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_SECTION,
    SELECT_MEDIUM_WIDTH,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_SMALL,
    TEXT_SIZE_LABEL,
    TEXT_SIZE_MEDIUM,
)
from app.features.usage.state import UsageState


def usage_filters() -> rx.Component:
    """Filters for usage buckets."""
    return rx.hstack(
        rx.text("Filters", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.select(
            UsageState.endpoints_name_list,
            on_change=UsageState.set_filter_endpoint,
            value=UsageState.filter_endpoint_value,
            width=SELECT_MEDIUM_WIDTH,
        ),
        rx.select(
            UsageState.available_models,
            on_change=UsageState.set_filter_model,
            value=UsageState.filter_model_value,
            width=SELECT_MEDIUM_WIDTH,
        ),
        rx.select(
            UsageState.available_keys,
            on_change=UsageState.set_filter_key,
            value=UsageState.filter_key_value,
            width=SELECT_MEDIUM_WIDTH,
        ),
        rx.text("From", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.input(
            type="date",
            value=UsageState.get_filter_date_from_value,
            on_change=UsageState.set_filter_date_from,
            max=UsageState.filter_date_to_value_max,
        ),
        rx.text("To", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.input(
            type="date",
            value=UsageState.get_filter_date_to_value,
            on_change=UsageState.set_filter_date_to,
        ),
        rx.button(
            "Apply",
            on_click=UsageState.apply_filters,
            align_self="end",
        ),
        spacing=SPACING_SMALL,
        align="center",
        wrap="wrap",
    )


def usage_summary_stat(label: str, value: rx.Var) -> rx.Component:
    return rx.vstack(
        rx.text(label, size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        rx.text(value, size=TEXT_SIZE_MEDIUM, weight="bold", color=rx.color("mauve", 12)),
        spacing="0",
        align="start",
    )


def usage_summary() -> rx.Component:
    """Totals over the selected date range."""
    return rx.hstack(
        usage_summary_stat("Prompt tokens", UsageState.summary_prompt_tokens),
        usage_summary_stat("Completion tokens", UsageState.summary_completion_tokens),
        usage_summary_stat("Total tokens", UsageState.summary_total_tokens),
        usage_summary_stat("Cost", UsageState.summary_cost),
        usage_summary_stat("kWh", UsageState.summary_kwh),
        usage_summary_stat("kgCO2eq", UsageState.summary_kgco2eq),
        spacing=SPACING_LARGE,
        wrap="wrap",
        width="100%",
    )


def usage_series_toggle(label: str, checked: rx.Var, on_change) -> rx.Component:
    return rx.hstack(
        rx.checkbox(checked=checked, on_change=on_change),
        rx.text(label, size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        spacing=SPACING_SMALL,
        align="center",
    )


def usage_chart() -> rx.Component:
    """Bar chart of daily usage buckets with toggleable metric series."""
    return rx.vstack(
        rx.hstack(
            usage_series_toggle("Prompt tokens", UsageState.show_prompt_tokens, UsageState.set_show_prompt_tokens),
            usage_series_toggle("Completion tokens", UsageState.show_completion_tokens, UsageState.set_show_completion_tokens),
            usage_series_toggle("Total tokens", UsageState.show_total_tokens, UsageState.set_show_total_tokens),
            usage_series_toggle("Cost", UsageState.show_cost, UsageState.set_show_cost),
            usage_series_toggle("kWh", UsageState.show_kwh, UsageState.set_show_kwh),
            usage_series_toggle("kgCO2eq", UsageState.show_kgco2eq, UsageState.set_show_kgco2eq),
            spacing=SPACING_MEDIUM,
            wrap="wrap",
            align="center",
        ),
        rx.cond(
            UsageState.chart_data.length() > 0,
            rx.recharts.bar_chart(
                rx.foreach(
                    UsageState.visible_chart_series,
                    lambda series: rx.recharts.bar(
                        data_key=series["data_key"],
                        name=series["name"],
                        fill=series["fill"],
                    ),
                ),
                rx.recharts.x_axis(data_key="date"),
                rx.recharts.y_axis(),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.graphing_tooltip(),
                rx.recharts.legend(),
                data=UsageState.chart_data,
                width="100%",
                height=360,
            ),
            rx.text("No usage in this period.", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
        ),
        spacing=SPACING_MEDIUM,
        width="100%",
    )


def usage_list() -> rx.Component:
    """Usage tracking page with filters, summary totals, and chart."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Daily usage", size=HEADING_SIZE_SECTION),
                rx.spacer(),
                usage_filters(),
                align="center",
                spacing=SPACING_SMALL,
                width="100%",
                wrap="wrap",
            ),
            rx.divider(),
            usage_summary(),
            rx.divider(),
            usage_chart(),
            spacing=SPACING_LARGE,
            width="100%",
        ),
        width="100%",
        spacing=SPACING_LARGE,
    )
