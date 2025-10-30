"""Chat domain models."""

from typing import TypedDict


class QA(TypedDict):
    """A question and answer pair."""

    question: str
    answer: str
