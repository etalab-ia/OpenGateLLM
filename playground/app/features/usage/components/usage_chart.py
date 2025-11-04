import reflex as rx

from app.features.usage.state import UsageState


def usage_chart() -> rx.Component:
    """Area chart showing requests per day."""
    return rx.vstack(
        rx.recharts.area_chart(
            rx.recharts.area(
                data_key="count",
                stroke=rx.color("accent", 9),
                fill=rx.color("accent", 5),
                type_="monotone",
            ),
            rx.recharts.x_axis(
                data_key="day",
                angle=-45,
                text_anchor="end",
                height=80,
            ),
            rx.recharts.y_axis(),
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
            ),
            rx.recharts.graphing_tooltip(),
            data=UsageState.requests_per_day,
            width="100%",
            height=300,
        ),
        spacing="3",
        width="100%",
    )
