from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ElasticsearchIndexLanguage(str, Enum):
    """
    The language of the Elasticsearch index, composed by the value, the stopwords and the stemmer.
    For more information about stemmer, see https://www.elastic.co/docs/reference/text-analysis/analysis-stemmer-tokenfilter#analysis-stemmer-tokenfilter-configure-parms.
    """

    ENGLISH = ("english", "_english_", "light_english")
    FRENCH = ("french", "_french_", "light_french")
    GERMAN = ("german", "_german_", "light_german")
    ITALIAN = ("italian", "_italian_", "light_italian")
    PORTUGUESE = ("portuguese", "_portuguese_", "light_portuguese")
    SPANISH = ("spanish", "_spanish_", "light_spanish")
    SWEDISH = ("swedish", "_swedish_", "light_swedish")

    def __new__(cls, value, stopwords, stemmer):
        if not isinstance(value, str):
            raise TypeError(f"Enum values must be strings (got {type(value).__name__})")
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.stopwords = stopwords
        obj.stemmer = stemmer

        return obj


class ElasticsearchChunk(BaseModel):
    id: int
    collection_id: int
    document_id: int
    document_name: str
    content: str
    embedding: list[float]
    metadata: dict | None
    created: datetime
