import logging
import os
from functools import lru_cache
from typing import Any, Iterator, List, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from api.utils.configuration import get_configuration

logger = logging.getLogger(__name__)

DEFAULT_PROMPTS_RELATIVE_DIR = "api/prompts"  # inside the repo
# language code WITHOUT extension (we append .j2 when resolving files)
DEFAULT_LANGUAGE = "en"


class PromptRenderer:
    """Render prompts from Jinja2 templates with override + fallback logic.

    Template resolution and macro fallback behavior:

    - The renderer builds an ordered list of available candidate templates for a module
        (overrides first, then internal templates). Example candidate names:
            - <module>.<language_file>
            - <language_file>
            - <module>.en.j2
            - en.j2

    - When rendering a macro, the renderer tries each candidate template in order and
        uses the first template that exposes the requested macro. This enables
        "partial overrides": you can drop a module-specific template into the
        overrides directory that only defines a subset of macros — missing macros
        will be resolved from the next candidate (usually the internal template).

    - The list of candidate templates is cached per module. Jinja2 template
        loading itself is LRU-cached, so repeated macro rendering is efficient.
    """

    def __init__(self, overrides_dir: str | None = None, language: str | None = None):
        configuration = get_configuration()
        settings = getattr(configuration, "settings", None)
        # read dynamic configuration if available
        self.overrides_dir = overrides_dir or getattr(settings, "prompts_dir", "/prompts")
        # prompts_lang is stored as a language code (eg 'en', 'fr') without the .j2 extension
        self.language = language or getattr(settings, "prompts_lang", DEFAULT_LANGUAGE)

        self.internal_dir = DEFAULT_PROMPTS_RELATIVE_DIR

        # Build environment list in order: overrides first (if exists), then internal
        search_paths = []
        if os.path.isdir(self.overrides_dir):
            search_paths.append(self.overrides_dir)
        else:
            logger.debug("Prompt overrides directory does not exist: %s", self.overrides_dir)
        search_paths.append(self.internal_dir)
        self.env = Environment(loader=FileSystemLoader(search_paths), autoescape=False, trim_blocks=True, lstrip_blocks=True)

        # cache of resolved template name lists per module key (ordered)
        self._module_template_cache: dict[Optional[str], List[str]] = {}
        # cache storing (base, template_name) pairs for actual resolution
        self._module_template_pairs_cache: dict[Optional[str], List[tuple[str, str]]] = {}

    def _candidate_templates(self, module: Optional[str]) -> List[str]:
        # candidates are actual template filenames (including .j2 extension)
        candidates: List[str] = []
        lang = self.language
        lang_fname = f"{lang}.j2"
        default_fname = f"{DEFAULT_LANGUAGE}.j2"

        if module:
            candidates.append(f"{module}.{lang_fname}")
        candidates.append(lang_fname)
        if module and lang != DEFAULT_LANGUAGE:
            candidates.append(f"{module}.{default_fname}")
        if lang != DEFAULT_LANGUAGE:
            candidates.append(default_fname)
        # ensure final fallback
        if default_fname not in candidates:
            candidates.append(default_fname)
        return candidates

    def _resolve_template_for_module(self, module: Optional[str]) -> Iterator[tuple[str, str]]:
        # If cached, yield cached template pairs
        if module in self._module_template_pairs_cache:
            yield from self._module_template_pairs_cache[module]
            return

        search_paths = [self.overrides_dir, self.internal_dir]
        candidates = self._candidate_templates(module)
        found: list[tuple[str, str]] = []

        # iterate candidates first so that for each candidate we can collect
        # both override and internal bases in order (overrides first)
        for cand in candidates:
            for base in search_paths:
                if not base or not os.path.isdir(base):
                    continue
                path = os.path.join(base, cand)
                if os.path.isfile(path) and (base, cand) not in found:
                    found.append((base, cand))

        if not found:
            # if no exact candidate matched, try to use any internal templates matching the language
            logger.debug(
                "No exact candidate template found; searching internal dir for any *.%s.j2 files",
                self.language,
            )
            try:
                internal_files = [f for f in os.listdir(self.internal_dir) if f.endswith(f".{self.language}.j2")]
            except OSError:
                internal_files = []

            if internal_files:
                found = [(self.internal_dir, f) for f in internal_files]
            else:
                # final fallback to default language file name (will be looked up in env paths)
                logger.error("No prompt template found; tried: %s", ", ".join(candidates))
                found = [(self.internal_dir, f"{DEFAULT_LANGUAGE}.j2")]

        # cache relative template names for introspection but keep pairs for loading
        # store as list of template filenames (for backward compatibility with tests that inspect cache)
        self._module_template_cache[module] = [cand for (_base, cand) in found]
        self._module_template_pairs_cache[module] = found
        yield from found

    @lru_cache
    def _get_template(self, base: str, template_name: str):
        # Load template from a specific base directory to allow loading internal
        # templates even when the same filename exists in an overrides dir.
        try:
            env = Environment(loader=FileSystemLoader([base]), autoescape=False, trim_blocks=True, lstrip_blocks=True)
            return env.get_template(template_name)
        except TemplateNotFound as e:
            raise FileNotFoundError(f"Prompt template file '{template_name}' not found in base '{base}'.") from e

    def render_macro(self, macro_name: str, /, module: str | None = None, **kwargs: Any) -> str:
        for base, template_name in self._resolve_template_for_module(module):
            try:
                template = self._get_template(base, template_name)
            except FileNotFoundError:
                # Race condition: file may have disappeared between listing and load; skip
                continue
            # Access macro
            try:
                macro = getattr(template.module, macro_name)
            except AttributeError:
                logger.debug(f"Macro '{macro_name}' not found in template '{template_name}' (base={base}).")
                continue
            return macro(**kwargs)
        raise ValueError(f"Macro '{macro_name}' not found in any template for module '{module}'.")


@lru_cache
def get_prompt_renderer() -> PromptRenderer:
    return PromptRenderer()
