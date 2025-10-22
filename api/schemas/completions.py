from collections.abc import Iterable

from openai.types import Completion
from pydantic import Field

from api.schemas import BaseModel
from api.schemas.usage import Usage


class CompletionRequest(BaseModel):
    prompt: str | list[str] | Iterable[int] | Iterable[Iterable[int]]
    model: str
    best_of: int | None = None
    echo: bool | None = False
    frequency_penalty: float | None = 0.0
    logit_bias: dict[str, float] | None = None
    logprobs: int | None = None
    max_tokens: int | None = 16
    n: int | None = 1
    presence_penalty: float | None = 0.0
    seed: int | None = None
    stop: str | list[str] | None = Field(default_factory=list)
    stream: bool | None = False
    suffix: str | None = None
    temperature: float | None = 1.0
    top_p: float | None = 1.0
    user: str | None = None


class Completions(Completion):
    id: str = Field(default=None, description="A unique identifier for the completion.")
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")
