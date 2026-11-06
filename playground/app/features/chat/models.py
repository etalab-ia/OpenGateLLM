"""Chat domain models."""

from typing import NotRequired, TypedDict


class ChatSource(TypedDict):
    """Display-ready provenance for a retrieved chunk."""

    chunk_id: int | None
    collection_id: int | None
    document_id: int | None
    document_name: str
    page_number: int | None
    content: str


class QA(TypedDict):
    """A question and answer pair."""

    question: str
    answer: str
    search_enabled: NotRequired[bool]
    sources_returned: NotRequired[bool]
    sources: NotRequired[list[ChatSource]]
