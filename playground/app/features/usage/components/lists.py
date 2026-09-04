"""Usage page composition."""

import reflex as rx

from app.core.variables import (
    HEADING_SIZE_FORM,
    HEADING_SIZE_SECTION,
    SELECT_MEDIUM_WIDTH,
    SPACING_LARGE,
    SPACING_SMALL,
    TEXT_SIZE_LABEL,
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
        rx.heading(value, size=HEADING_SIZE_SECTION, color=rx.color("mauve", 12)),
        spacing="0",
        align="center",
        flex="1",
        min_width="120px",
    )


def usage_summary() -> rx.Component:
    """Totals over the selected date range."""
    return rx.hstack(
        usage_summary_stat("Requests", UsageState.summary_requests),
        usage_summary_stat("Prompt tokens", UsageState.summary_prompt_tokens),
        usage_summary_stat("Completion tokens", UsageState.summary_completion_tokens),
        usage_summary_stat("Total tokens", UsageState.summary_total_tokens),
        usage_summary_stat("Cost", UsageState.summary_cost),
        usage_summary_stat("kWh", UsageState.summary_kwh),
        usage_summary_stat("kgCO2eq", UsageState.summary_kgco2eq),
        spacing=SPACING_LARGE,
        wrap="wrap",
        width="100%",
        justify="center",
        align="center",
    )


def usage_metric_chart(title: str, *bars: rx.Component, bar_gap: int = 4) -> rx.Component:
    return rx.vstack(
        rx.heading(title, size=HEADING_SIZE_FORM, color=rx.color("mauve", 12)),
        rx.recharts.bar_chart(
            *bars,
            rx.recharts.x_axis(data_key="date"),
            rx.recharts.graphing_tooltip(),
            data=UsageState.chart_data,
            width="100%",
            height=260,
            bar_gap=bar_gap,
        ),
        spacing=SPACING_SMALL,
        width="100%",
    )


def usage_charts() -> rx.Component:
    """One bar chart per metric; tokens stack, impacts group kWh and kgCO2eq."""
    return rx.cond(
        UsageState.chart_data.length() > 0,
        rx.grid(
            usage_metric_chart(
                "Requests",
                rx.recharts.bar(
                    data_key="requests",
                    name="Requests",
                    stroke=rx.color("accent", 9),
                    fill=rx.color("accent", 8),
                ),
            ),
            usage_metric_chart(
                "Tokens",
                rx.recharts.bar(
                    data_key="prompt_tokens",
                    name="Prompt tokens",
                    stroke=rx.color("green", 9),
                    fill=rx.color("green", 8),
                    stack_id="tokens",
                ),
                rx.recharts.bar(
                    data_key="completion_tokens",
                    name="Completion tokens",
                    stroke=rx.color("accent", 9),
                    fill=rx.color("accent", 8),
                    stack_id="tokens",
                ),
            ),
            usage_metric_chart(
                "Cost",
                rx.recharts.bar(
                    data_key="cost",
                    name="Cost",
                    stroke=rx.color("accent", 9),
                    fill=rx.color("accent", 8),
                ),
            ),
            usage_metric_chart(
                "Impacts",
                rx.recharts.bar(
                    data_key="kWh",
                    name="kWh",
                    stroke=rx.color("accent", 9),
                    fill=rx.color("accent", 8),
                ),
                rx.recharts.bar(
                    data_key="kgCO2eq",
                    name="kgCO2eq",
                    stroke=rx.color("green", 9),
                    fill=rx.color("green", 8),
                ),
                bar_gap=0,
            ),
            columns="2",
            spacing=SPACING_LARGE,
            width="100%",
        ),
        rx.text("No usage in this period.", size=TEXT_SIZE_LABEL, color=rx.color("mauve", 11)),
    )


def usage_list() -> rx.Component:
    """Usage tracking page with filters, summary totals, and charts."""
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
            usage_charts(),
            spacing=SPACING_LARGE,
            width="100%",
        ),
        width="100%",
        spacing=SPACING_LARGE,
    )
