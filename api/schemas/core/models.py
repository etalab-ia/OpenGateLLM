from enum import Enum

from pydantic import BaseModel, Field, RootModel, conint


# TEI
class TruncationDirection(Enum):
    left = "left"
    right = "right"


class TEICreateRerank(BaseModel):
    query: str = Field(..., examples=["What is Deep Learning?"])
    raw_scores: bool = Field(False, examples=[False])
    return_text: bool = Field(False, examples=[False])
    texts: list[str] = Field(..., examples=[["Deep Learning is ..."]])
    truncate: bool | None = Field(False, examples=[False])
    truncation_direction: TruncationDirection = "right"


class Rank(BaseModel):
    index: conint(ge=0) = Field(..., examples=["0"])
    score: float = Field(..., examples=["1.0"])
    text: str | None = Field(None, examples=["Deep Learning is ..."])


class TEIReranks(RootModel[list[Rank]]):
    root: list[Rank]
