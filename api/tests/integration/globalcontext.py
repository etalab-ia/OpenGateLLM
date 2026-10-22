from contextlib import contextmanager

from api.infrastructure.context import GlobalContext, global_context


@contextmanager
def override_global_context(**overrides):
    unknown = sorted(set(overrides) - set(GlobalContext.model_fields))
    if unknown:
        raise AttributeError(f"GlobalContext has no field {unknown}: the override would silently do nothing.")

    previous = {key: getattr(global_context, key) for key in overrides}
    for key, value in overrides.items():
        setattr(global_context, key, value)
    try:
        yield
    finally:
        for key, value in previous.items():
            setattr(global_context, key, value)
