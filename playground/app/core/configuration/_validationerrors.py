from functools import wraps
from typing import Any, get_args

from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

DOCUMENTATION_URL = "https://docs.opengatellm.org/configuration/configuration_file"


class ConfigurationValidationError(Exception):
    def __init__(self, validation_error: PydanticValidationError, root_schema: type[BaseModel]):
        message = str(validation_error)
        for error in validation_error.errors():
            error_location = tuple(error.get("loc", ()))
            documentation_url = _section_documentation_url(root_schema, error_location)
            original_line = f"    For further information visit {error['url']}"
            replacement_line = f"    For further information visit {documentation_url}"
            message = message.replace(original_line, replacement_line, 1)
        super().__init__(message)


def _section_documentation_url(root_schema: type[BaseModel], error_location: tuple[Any, ...]) -> str:
    documentation_url = DOCUMENTATION_URL
    schema = root_schema
    for segment in error_location:
        if not isinstance(segment, str):  # an index in a list
            continue
        field = schema.model_fields.get(segment)
        nested_schema = _nested_schema(field.annotation) if field else None
        if nested_schema is None:
            break
        schema = nested_schema
        documentation_url = f"{DOCUMENTATION_URL}#{schema.__name__.lower()}"
    return documentation_url


def _nested_schema(annotation: Any) -> type[BaseModel] | None:
    candidates = get_args(annotation) or (annotation,)
    return next((candidate for candidate in candidates if isinstance(candidate, type) and issubclass(candidate, BaseModel)), None)


def custom_validation_error(cls: type[BaseModel]):
    """Raise a ConfigurationValidationError, which links each error to its section of the documentation, instead of Pydantic's ValidationError."""
    original_init = cls.__init__

    @wraps(original_init)
    def new_init(self, **data):
        try:
            original_init(self, **data)
        except PydanticValidationError as e:
            raise ConfigurationValidationError(validation_error=e, root_schema=cls) from None  # hide previous traceback

    cls.__init__ = new_init
    return cls


class HiddenInputSchema(BaseModel):
    model_config = ConfigDict(extra="allow", hide_input_in_errors=True)
