from fastapi import Form

from api.utils.prompt_loader import get_prompt_renderer


def get_default_ocr_prompt() -> str:
    """Load the OCR default prompt from templates."""
    renderer = get_prompt_renderer()
    try:
        return renderer.render_macro("default_ocr", module="ocr").strip()
    except Exception as e:
        raise RuntimeError(
            "Prompt macro 'default_ocr' for module 'ocr' not found or failed to render. Ensure app/prompts/ocr.*.j2 defines this macro."
        ) from e


DEFAULT_PROMPT = get_default_ocr_prompt()

ModelForm: str = Form(default=..., description="The model to use for the OCR.")  # fmt: off
DPIForm: int = Form(default=150, ge=100, le=600, description="The DPI to use for the OCR (each page will be rendered as an image at this DPI).")  # fmt: off
PromptForm: str = Form(default=DEFAULT_PROMPT, description="The prompt to use for the OCR.")  # fmt: off
