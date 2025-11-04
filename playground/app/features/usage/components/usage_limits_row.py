"""Individual limits row component."""

import reflex as rx

from app.features.usage.state import UsageState


def usage_limits_row(model: str) -> rx.Component:
    """Display a row with all limits for a model."""
    limits = UsageState.limits_by_model[model]

    def limit_cell(limit_type: str) -> rx.Component:
        """Create a cell for a limit value."""
        value = limits[limit_type]
        return rx.table.cell(
            rx.match(
                value,
                (None, rx.text("Unlimited", size="2", color=rx.color("mauve", 11))),
                rx.text(value, weight="medium", size="2"),
            ),
        )

    return rx.table.row(
        rx.table.cell(rx.text(model, weight="medium", size="2")),
        limit_cell("rpm"),
        limit_cell("rpd"),
        limit_cell("tpm"),
        limit_cell("tpd"),
    )
