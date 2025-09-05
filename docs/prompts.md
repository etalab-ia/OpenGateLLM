# Prompt Management System

The API now supports external prompt templates using **Jinja2**. This allows you to:

- Centralize prompt definitions
- Localize prompts per language
- Override built‑in prompts at runtime (Docker volume)
- Keep Python code clean & maintainable

## Directory Structure

Built-in templates (do not modify in production):
```
/app/prompts/
  en.j2
  fr.j2
```

Override directory (mount in Docker):
```
/prompts/
  fr.j2        # or any other language file
  en.j2        # optional override
```

## Configuration
Add (or override) in `config.yml` under `settings`:
```yaml
settings:
  prompts_dir: /prompts    # where override templates are mounted
  prompts_lang: fr       # selects the language (do NOT include the .j2 extension)
```
Defaults:
- `prompts_dir`: `/prompts`
- `prompts_lang`: `en`

If the selected language file is missing in the override directory, the system falls back to the internal file.
If still missing, it falls back to `en.j2` internally.

Important: partial overrides and macro fallback
---------------------------------------------
The renderer doesn't just pick a single template and stop. Instead, for each module
it builds an ordered list of available candidate templates (overrides first, then
internal). When you ask the renderer to render a macro, it will try each candidate
in turn until it finds a template that defines the requested macro. This means:

- You can provide a `multiagent.en.j2` override that only customizes a couple of
  macros; the renderer will use your custom macros and fall back to the built-in
  templates for macros you didn't override.
- If a module-specific template is present but doesn't define the requested macro,
  the renderer will transparently try the next candidate (e.g. the generic
  `en.j2` or other internal templates).

This behavior makes it easy to incrementally override prompts without copying
the entire file.

## Template API (Macros)
Each language file defines the following macros:
- `teller_1(doc, question)` – Context‑grounded answer generator
- `teller_2(question)` – General lightweight answer generator
- `choicer(prompt, docs)` – Classification prompt deciding which strategy to apply
- `concat(answers, prompt)` – Synthesis of multiple agent answers

Example (excerpt of `fr.j2`):
```jinja2
{% macro teller_1(doc, question) %}
... prompt text ...
question : {{ question }}
réponse ("Rien ici" ou ta réponse):
{% endmacro %}
```

## How It Works
The class `MultiAgentManager` loads prompts via `PromptRenderer`:
```python
from app.utils.prompt_loader import get_prompt_renderer
renderer = get_prompt_renderer()
text = renderer.render_macro("teller_1", doc=..., question=...)
```
The renderer:
1. Builds a Jinja2 environment with search paths = `[prompts_dir(if exists), app/prompts]`
2. Selects `prompts_lang` (language code) file; falls back to internal version; then to `en`
3. Caches the loaded template and exposes macro rendering

## Adding a New Language
1. Copy `en.j2` to `es.j2` (for example)
2. Translate macro bodies, keep macro names and parameters unchanged
3. Set `prompts_lang: es` in configuration
4. (Optional) Mount custom overrides at runtime

## Docker Override
In your `docker-compose.yml`:
```yaml
services:
  api:
    volumes:
      - ./my-prompts:/prompts
    environment:
  - PROMPTS_LANG=fr   # or set in config.yml
```
Ensure `config.yml` contains:
```yaml
settings:
  prompts_dir: /prompts
  prompts_lang: fr
```

## Validation / Troubleshooting
- Missing macro → 400/500 error with message: `Macro '<name>' not found`
- Missing language file → Warning log + fallback to `en.j2`
- Permission issues in mounted dir → The override directory is skipped (logged at DEBUG)

## Extending Beyond MultiAgentManager
Other components can migrate similarly:
1. Identify hard‑coded prompt strings
2. Add equivalent macros to each language file
3. Replace in code with `renderer.render_macro(...)`

---
For questions, see `app/utils/prompt_loader.py` for implementation details.
