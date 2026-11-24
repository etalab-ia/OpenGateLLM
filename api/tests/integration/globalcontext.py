from contextlib import contextmanager
from unittest.mock import create_autospec

from api.domain.model import ModelTokenizer, ModelTokenizerLoader
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


def create_mock_model_tokenizer_loader(tokens: int = 10) -> ModelTokenizerLoader:
    """A loader whose tokenizer counts `tokens` for any non-empty text and 0 otherwise."""
    tokenizer = create_autospec(ModelTokenizer, instance=True, spec_set=True)
    tokenizer.compute_tokens.side_effect = lambda texts: tokens if " ".join(texts).strip() else 0
    loader = create_autospec(ModelTokenizerLoader, instance=True, spec_set=True)
    loader.load.return_value = tokenizer
    return loader
