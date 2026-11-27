from api.dependencies import _tokenizer_registry
from api.infrastructure.huggingface import HuggingFaceTokenizerRegistry
from api.tests.integration.globalcontext import override_global_context


def test_should_return_the_registry_held_by_the_global_context_on_every_call():
    registry = HuggingFaceTokenizerRegistry()

    with override_global_context(tokenizer_registry=registry):
        assert _tokenizer_registry() is registry
        assert _tokenizer_registry() is _tokenizer_registry()
