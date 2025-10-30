"""Rate limits state management."""

from app.features.keys.state import KeysState


class LimitsState(KeysState):
    """Rate limits state - inherits from KeysState to access limits data."""

    # This state inherits all limit-related computed vars from KeysState:
    # - formatted_limits
    # - limits_by_model
    # - models_list
    pass
