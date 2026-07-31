"""Right sidebar with sampling parameters."""

import reflex as rx

from app.core.variables import ICON_SIZE_TINY
from app.features.chat.state import ChatState


def param_section(title: str, children: list, description: str | None = None) -> rx.Component:
    """Create a parameter section.

    Args:
        title: The section title.
        children: The child components.
        description: Optional tooltip description.

    Returns:
        A parameter section component.
    """
    title_content = (
        rx.hstack(
            rx.text(
                title,
                size="2",
                weight="bold",
                color=rx.color("mauve", 12),
            ),
            rx.tooltip(
                rx.icon("info", size=ICON_SIZE_TINY, color=rx.color("mauve", 10)),
                content=description,
            ),
            spacing="1",
            align="center",
        )
        if description
        else rx.text(
            title,
            size="2",
            weight="bold",
            color=rx.color("mauve", 12),
        )
    )

    return rx.vstack(
        title_content,
        *children,
        spacing="2",
        width="100%",
        padding="0.5em",
    )


def chat_params_sidebar() -> rx.Component:
    """Right sidebar with sampling parameters."""
    return rx.box(
        # Use a regular vstack instead of scroll_area so the sidebar itself doesn't scroll
        rx.vstack(
            rx.heading(
                "Parameters",
                size="4",
                color=rx.color("mauve", 12),
                margin_bottom="0.5em",
            ),
            # Model selection
            param_section(
                "Model",
                [
                    rx.cond(
                        ChatState.available_models.length() > 0,
                        rx.select(
                            ChatState.available_models,
                            value=ChatState.model,
                            on_change=ChatState.set_model,
                            placeholder="Select a model",
                            width="100%",
                        ),
                        rx.hstack(
                            rx.spinner(loading=ChatState.models_loading, size="2"),
                            rx.text(
                                rx.cond(
                                    ChatState.models_loading,
                                    "Loading models...",
                                    "No models available",
                                ),
                                size="2",
                                color=rx.color("mauve", 10),
                            ),
                            width="100%",
                        ),
                    ),
                ],
            ),
            # Temperature
            param_section(
                "Temperature",
                [
                    rx.hstack(
                        rx.slider(
                            default_value=[ChatState.temperature],
                            on_value_commit=lambda value: ChatState.set_temperature(value[0]),
                            min=0,
                            max=2,
                            step=0.1,
                            flex="1",
                        ),
                        rx.text(
                            ChatState.temperature,
                            size="2",
                            color=rx.color("mauve", 11),
                            min_width="3ch",
                        ),
                        width="100%",
                    ),
                ],
                description="Controls randomness. Lower values (0.0-0.7) are more focused and deterministic, higher values (0.7-2.0) are more creative and random.",
            ),
            # Top P
            param_section(
                "Top P",
                [
                    rx.hstack(
                        rx.slider(
                            default_value=[ChatState.top_p],
                            on_value_commit=lambda value: ChatState.set_top_p(value[0]),
                            min=0,
                            max=1,
                            step=0.01,
                            flex="1",
                        ),
                        rx.text(
                            ChatState.top_p,
                            size="2",
                            color=rx.color("mauve", 11),
                            min_width="4ch",
                        ),
                        width="100%",
                    ),
                ],
                description="Nucleus sampling threshold. Controls diversity by considering only the top P probability mass. Lower values are more focused.",
            ),
            # Max Tokens
            param_section(
                "Max completion tokens",
                [
                    rx.hstack(
                        rx.slider(
                            default_value=[ChatState.max_completion_tokens],
                            on_value_commit=lambda value: ChatState.set_max_completion_tokens(value[0]),
                            min=1,
                            max=4096,
                            step=1,
                            flex="1",
                        ),
                        rx.text(
                            ChatState.max_completion_tokens,
                            size="2",
                            color=rx.color("mauve", 11),
                            min_width="5ch",
                        ),
                        width="100%",
                    ),
                ],
                description="Maximum number of tokens to generate in the completion. Higher values allow longer responses but may be slower.",
            ),
            # Frequency Penalty
            param_section(
                "Frequency penalty",
                [
                    rx.hstack(
                        rx.slider(
                            default_value=[ChatState.frequency_penalty],
                            on_value_commit=lambda value: ChatState.set_frequency_penalty(value[0]),
                            min=-2,
                            max=2,
                            step=0.1,
                            flex="1",
                        ),
                        rx.text(
                            ChatState.frequency_penalty,
                            size="2",
                            color=rx.color("mauve", 11),
                            min_width="4ch",
                        ),
                        width="100%",
                    ),
                ],
                description="Penalizes tokens based on their frequency. Positive values reduce repetition, negative values encourage it.",
            ),
            # Presence Penalty
            param_section(
                "Presence penalty",
                [
                    rx.hstack(
                        rx.slider(
                            default_value=[ChatState.presence_penalty],
                            on_value_commit=lambda value: ChatState.set_presence_penalty(value[0]),
                            min=-2,
                            max=2,
                            step=0.1,
                            flex="1",
                        ),
                        rx.text(
                            ChatState.presence_penalty,
                            size="2",
                            color=rx.color("mauve", 11),
                            min_width="4ch",
                        ),
                        width="100%",
                    ),
                ],
                description="Penalizes tokens based on their presence in the text. Positive values encourage new topics, negative values encourage staying on topic.",
            ),
            # Seed
            param_section(
                "Seed",
                [
                    rx.input(
                        placeholder="Random seed",
                        value=ChatState.seed_str,
                        on_change=ChatState.set_seed_str,
                        type="number",
                        width="100%",
                        size="2",
                    ),
                ],
                description="Random seed for deterministic results. Use the same seed with the same parameters to get reproducible outputs.",
            ),
            # Stop sequences
            param_section(
                "Stop sequences",
                [
                    rx.text_area(
                        placeholder="Stop sequences (one per line)",
                        value=ChatState.stop_sequences,
                        on_change=ChatState.set_stop_sequences,
                        width="100%",
                        min_height="60px",
                        size="2",
                    ),
                ],
                description="Sequences where the API will stop generating further tokens. Enter one sequence per line.",
            ),
            spacing="2",
            width="100%",
            padding="0.75em",
            on_mount=ChatState.load_models,
        ),
        width="320px",
        height="100%",
        background_color=rx.color("mauve", 2),
        border_left=f"1px solid {rx.color("mauve", 3)}",
    )
