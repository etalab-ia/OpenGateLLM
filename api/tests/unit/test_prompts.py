from api.utils.prompt_loader import PromptRenderer, get_prompt_renderer
from api.schemas.ocr import get_default_ocr_prompt


def test_multiagent_module_specific_template():
    renderer = PromptRenderer(language="en")
    out = renderer.render_macro("teller_1", module="multiagent", doc="Law context", question="Quel est le sujet ?")
    assert "administrative assistant" in out.lower()
    # ensure module-specific file chosen (cached list contains module file as first candidate)
    assert isinstance(renderer._module_template_cache["multiagent"], list)
    assert any(item.startswith("multiagent.en.j2") for item in renderer._module_template_cache["multiagent"])


def test_fallback_unknown_module_uses_generic_en():
    renderer = PromptRenderer(language="en")
    out = renderer.render_macro("teller_1", module="unknownmod", doc="Context", question="Question?")
    assert "assistant" in out.lower()
    assert isinstance(renderer._module_template_cache["unknownmod"], list)
    # ensure at least one internal language template was collected as a fallback
    assert any(item.endswith(".en.j2") for item in renderer._module_template_cache["unknownmod"])


def test_language_fallback_to_en_when_missing():
    # language file xx.j2 does not exist; should fallback to multiagent.en.j2
    renderer = PromptRenderer(language="xx")
    out = renderer.render_macro("teller_2", module="multiagent", question="Quelle est la capitale de la France ?")
    assert "france" in out.lower()
    assert isinstance(renderer._module_template_cache["multiagent"], list)
    assert "multiagent.en.j2" in renderer._module_template_cache["multiagent"]


def test_ocr_default_prompt_macro():
    prompt = get_default_ocr_prompt()
    assert len(prompt) > 20
    assert "markdown" in prompt.lower()


def test_renderer_cache_does_not_cross_modules():
    renderer = PromptRenderer(language="en")
    renderer.render_macro("teller_1", module="multiagent", doc="X", question="Y")
    renderer.render_macro("query", module="websearch", prompt="test")
    assert set(renderer._module_template_cache.keys()) == {"multiagent", "websearch"}


def test_get_prompt_renderer_singleton():
    get_prompt_renderer.cache_clear()
    r1 = get_prompt_renderer()
    r2 = get_prompt_renderer()
    assert r1 is r2


def test_macro_fallback_across_candidates(tmp_path):
    # create an overrides directory containing a module-specific template
    # that intentionally lacks the 'teller_1' macro. The renderer should
    # then try the next candidate and find the macro in the internal template.
    overrides = tmp_path / "prompts"
    overrides.mkdir()

    # module-specific template without teller_1 macro
    module_file = overrides / "multiagent.en.j2"
    module_file.write_text("{# module-specific override without teller_1 #}\n{% macro other()%}nope{% endmacro %}\n")

    renderer = PromptRenderer(overrides_dir=str(overrides), language="en")

    # Should return content coming from the internal multiagent.en.j2 (has teller_1 macro)
    out = renderer.render_macro("teller_1", module="multiagent", doc="Ctx", question="Q?")
    assert "administrative assistant" in out.lower()
