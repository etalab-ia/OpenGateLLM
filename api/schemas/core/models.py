from enum import Enum
from http import HTTPMethod
from typing import Literal

from pydantic import BaseModel, Field

from api.utils import variables

Endpoint = Enum("Endpoint", {name.upper(): value for name, value in vars(variables).items() if name.startswith("ENDPOINT__")}, type=str)


class RequestContent(BaseModel):
    method: HTTPMethod
    model: str = Field(description="The called model name.")
    endpoint: Endpoint = Field(description="The source endpoint (at the user side) of the request.")
    json: dict = Field(default={}, description="The JSON body to use for the request.")
    form: dict = Field(default={}, description="The form-encoded data to use for the request.")
    files: dict = Field(default={}, description="The files to use for the request.")
    additional_data: dict = Field(default={}, description="The additional data to add to the response.")

    # @TODO: add a build method to build the request content from a request (after clean architecture refactor)


class Metric(str, Enum):
    TTFT = "ttft"  # time to first token
    LATENCY = "latency"  # requests latency
    INFLIGHT = "inflight"  # requests concurrency
    PERFORMANCE = "performance"  # custom performance metric


# Marker
class MarkerCreateOCR(BaseModel):
    page_range: str = Field(default="", description="Page range to convert, specify comma separated page numbers or ranges. Example: '0,5-10,20'")  # fmt: off
    force_ocr: bool = Field(default=False, description="Force OCR on all pages of the PDF.  Defaults to False.  This can lead to worse results if you have good text in your PDFs (which is true in most cases).")  # fmt: off
    paginate_output: bool = Field(default=False, description="Whether to paginate the output.  Defaults to False.  If set to True, each page of the output will be separated by a horizontal rule that contains the page number (2 newlines, {PAGE_NUMBER}, 48 - characters, 2 newlines).")  # fmt: off
    output_format: Literal["markdown", "json", "html"] = Field(default="markdown", description="The format to output the text in.  Can be 'markdown', 'json', or 'html'.  Defaults to 'markdown'.")  # fmt: off


# TEI
class TEICreateRerank(BaseModel):
    query: str = Field(..., examples=["What is Deep Learning?"])
    raw_scores: bool = Field(False, examples=[False])
    return_text: bool = Field(False, examples=[False])
    texts: list[str] = Field(..., examples=[["Deep Learning is ..."]])
    truncate: bool | None = Field(False, examples=[False])
    truncation_direction: Literal["left", "right"] = Field(default="right")
